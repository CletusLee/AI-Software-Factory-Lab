"""OpenAI Chat Completions adapter for the local AgentOS demo."""
import hashlib
import json
import os
import secrets
import time
import uuid

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.responses import FileResponse
from integration.registry import load

app = FastAPI()
registry = load()
TARGETS = {key: (kind, key) for kind in ('teams', 'agents') for key in registry[kind]}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/report")
async def report():
    return FileResponse("/data/native-report.html", media_type="text/html")


@app.get("/v1/models")
async def models():
    return {"object": "list", "data": [
        {"id": name, "object": "model", "created": 0, "owned_by": "agno"}
        for name in TARGETS
    ]}


@app.post("/v1/chat/completions")
async def completions(request: Request, x_user_id: str = Header(default=""),
                      x_conversation_id: str = Header(default=""),
                      authorization: str = Header(default="")):
    expected = "Bearer " + os.environ["OS_SECURITY_KEY"]
    if not secrets.compare_digest(authorization, expected):
        raise HTTPException(401, "Invalid credentials")
    body = await request.json()
    target = TARGETS.get(body.get("model"))
    if not target:
        raise HTTPException(400, "Unknown AgentOS target")
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        raise HTTPException(400, "messages must be a non-empty list")
    transcript = []
    for message in messages:
        content = message.get("content")
        if not isinstance(content, str):
            raise HTTPException(400, "Only text messages are supported")
        if message.get("role") in ("system", "user", "assistant"):
            transcript.append(f'{message["role"]}: {content}')
    if not transcript or messages[-1].get("role") != "user":
        raise HTTPException(400, "The last message must be from the user")
    identity = x_user_id or str(body.get("user") or "local-user")
    conversation = x_conversation_id or str(uuid.uuid4())
    session = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{identity}:{conversation}:{body['model']}"))
    user_id = hashlib.sha256(identity.encode()).hexdigest()
    headers = {"Authorization": "Bearer " + os.environ["OS_SECURITY_KEY"]}
    url = f'{os.getenv("AGENTOS_URL", "http://agentos:7777")}/{target[0]}/{target[1]}/runs'
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(url, headers=headers, data={
                "message": "\n\n".join(transcript),
                "session_id": session,
                "user_id": user_id,
                "stream": "false",
            })
            response.raise_for_status()
            result = response.json()
    except httpx.HTTPError as error:
        raise HTTPException(502, "AgentOS request failed") from error
    if result.get("status") in ("ERROR", "FAILED", "CANCELLED"):
        raise HTTPException(502, "AgentOS run failed")
    content = result.get("content")
    if content is None:
        raise HTTPException(502, "AgentOS returned no response")
    if not isinstance(content, str):
        content = json.dumps(content, ensure_ascii=False)
    run_id = "chatcmpl-" + uuid.uuid4().hex
    created = int(time.time())
    base = {"id": run_id, "created": created, "model": body["model"]}
    if body.get("stream"):
        async def events():
            for delta, finish in (({"role": "assistant", "content": content}, None), ({}, "stop")):
                chunk = {**base, "object": "chat.completion.chunk",
                         "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}
                yield "data: " + json.dumps(chunk, ensure_ascii=False) + "\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(events(), media_type="text/event-stream")
    return {**base, "object": "chat.completion", "choices": [
        {"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}
    ]}

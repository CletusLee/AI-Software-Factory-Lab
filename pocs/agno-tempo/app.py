import json
import os
import re
import subprocess
import sys
from pathlib import Path
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.db.postgres import PostgresDb
from agno.os import AgentOS
from integration.registry import load
from agno.skills import Skills, LocalSkills

registry = load()

# 1. 設定 OpenTelemetry -> Grafana Tempo
otel_endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "").strip()

if otel_endpoint:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from openinference.instrumentation.agno import AgnoInstrumentor

    provider = TracerProvider()
    exporter = OTLPSpanExporter(endpoint=otel_endpoint, timeout=5)
    provider.add_span_processor(BatchSpanProcessor(
        exporter,
        schedule_delay_millis=1000,
        export_timeout_millis=5000,
    ))
    trace.set_tracer_provider(provider)
    AgnoInstrumentor().instrument()
    print(f"[Observability] OTLP tracing enabled: {otel_endpoint}")
else:
    print("[Observability] OTEL_EXPORTER_OTLP_TRACES_ENDPOINT is empty; running without trace export.")

# 2. 連接 PostgreSQL (儲存 Session、Run 與 Trace)
db = PostgresDb(db_url=os.getenv("DATABASE_URL"))

# 3. 範例 Tool：模擬第 1/2 課的 Ticket 依賴與證據檢查
def check_ticket_readiness(work_item_id: str, scenario: str = "stale") -> dict:
    """查詢 repository 中的工作項目 fixture；不連接外部工單或 CI 系統。"""
    work_id = work_item_id.strip().upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{0,63}", work_id):
        return {"work_item_id": work_item_id, "recommendation": "UNKNOWN", "reason": "工作項目 ID 格式無效"}
    scenario_dir = (Path('/app/scenarios') / work_id.lower()).resolve()
    if Path('/app/scenarios').resolve() not in scenario_dir.parents:
        return {"work_item_id": work_id, "recommendation": "UNKNOWN", "reason": "工作項目路徑無效"}
    try:
        work_item = json.loads((scenario_dir / 'work-item.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {"work_item_id": work_id, "recommendation": "UNKNOWN", "reason": "本機範例中沒有此工作項目"}
    if work_item.get('id') != work_id:
        return {"work_item_id": work_id, "recommendation": "UNKNOWN", "reason": "工作項目定義 ID 不符"}
    if scenario not in ("stale", "passed", "timeout"):
        return {"work_item_id": work_id, "recommendation": "UNKNOWN", "reason": "未知示範情境"}
    result = {
        "work_item_id": work_id,
        "scenario": scenario,
        "source": "repository 工作項目 fixture；外部工單或 CI 非實際紀錄",
        "target_transition": "Release Review",
        "candidate_commit": "a1b2c3d",
        "spec": {"status": "approved", "ref": f"local-demo://spec/{work_id}-v1", "owner": "模擬 Domain Owner"},
        "oracle": {"status": "approved", "ref": f"local-demo://oracle/{work_id}-v1", "owner": "模擬 QA"},
        "note": "此為送審建議，正式驗收與發布由授權人員決定。",
    }
    if scenario == "timeout":
        result.update({"ci": {"status": "UNKNOWN", "reason": "模擬 CI 查詢逾時"}, "recommendation": "UNKNOWN", "reason": "無法確認候選版本測試結果"})
    elif scenario == "stale":
        result.update({"ci": {"status": "PASS", "tested_commit": "f0e1d2c", "ref": "local-demo://ci/run-101"}, "recommendation": "NOT READY", "reason": "綠燈測試的 commit 與候選版本不一致"})
    else:
        try:
            test_run = subprocess.run([sys.executable, '-m', 'unittest', '-v', 'test_payment_demo'], capture_output=True, text=True, timeout=30, check=False)
            test_status = "PASS" if test_run.returncode == 0 else "FAIL"
            result.update({"ci": {"status": test_status, "tested_commit": "a1b2c3d", "ref": "local-demo://ci/run-102", "note": "在容器內實際執行本機範例測試；commit 與 CI ref 為模擬", "test_output": (test_run.stdout + test_run.stderr)[-3000:]}, "recommendation": "READY" if test_run.returncode == 0 else "NOT READY", "reason": "本機測試通過，模擬核准與版本資料齊備" if test_run.returncode == 0 else "本機測試未通過"})
        except (OSError, subprocess.TimeoutExpired):
            result.update({"ci": {"status": "UNKNOWN", "reason": "本機測試無法執行或逾時"}, "recommendation": "UNKNOWN", "reason": "無法確認測試結果"})
    return result

# 4. 建立試點 Agent
factory_agent = Agent(
    id="sdlc-ticket-agent",
    name="SDLC Ticket & Spec Assistant",
    model=OpenAIChat(
        id=os.getenv("MODEL_ID", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    ),
    db=db,
    tools=[check_ticket_readiness],
    instructions=[registry['agents']['sdlc-ticket-agent']['prompt']],
    skills=Skills(loaders=[LocalSkills(str(registry['root'] / 'skills' / skill))
                           for skill in registry['agents']['sdlc-ticket-agent']['skills']]),
    markdown=True,
)

# 5. 初始化 AgentOS (強制關閉 Agno 外部遙測)
from native_workflows import make_agents, make_teams, build_workflows

demo_agents = make_agents()
demo_teams = make_teams(demo_agents, db)
demo_workflows = build_workflows(demo_agents, demo_teams, db)

agent_os = AgentOS(
    agents=[factory_agent, *demo_agents.values()],
    teams=demo_teams,
    workflows=demo_workflows,
    telemetry=False,
)


class AgentOSRunTraceEnricher:
    """Add AgentOS run identifiers to the active HTTP server span."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        parts = path.strip("/").split("/")
        is_run_request = (
            scope.get("type") == "http"
            and scope.get("method") == "POST"
            and len(parts) == 3
            and parts[0] in {"agents", "teams", "workflows"}
            and parts[2] == "runs"
        )
        if not is_run_request:
            await self.app(scope, receive, send)
            return

        from opentelemetry import trace

        server_span = trace.get_current_span()
        pending_event = bytearray()

        def add_run_attributes(payload):
            if not isinstance(payload, dict) or not payload.get("run_id"):
                return
            if not server_span.is_recording():
                return
            server_span.set_attribute("agno.run_id", str(payload["run_id"]))
            session_id = payload.get("session_id")
            if session_id:
                server_span.set_attribute("agno.session_id", str(session_id))
                server_span.set_attribute("session.id", str(session_id))
            server_span.set_attribute("agno.component.type", parts[0][:-1])
            server_span.set_attribute("agno.component.id", parts[1])

        def parse_response_line(line):
            line = line.strip()
            if line.startswith(b"data:"):
                line = line[5:].strip()
            if not line or line == b"[DONE]":
                return
            try:
                payload = json.loads(line)
            except (UnicodeDecodeError, ValueError):
                return
            add_run_attributes(payload)

        async def capture_response(message):
            if message.get("type") == "http.response.body":
                pending_event.extend(message.get("body", b""))
                while b"\n" in pending_event:
                    line, _, remainder = pending_event.partition(b"\n")
                    pending_event[:] = remainder
                    parse_response_line(line)
                if not message.get("more_body", False):
                    parse_response_line(pending_event)
            await send(message)

        await self.app(scope, receive, capture_response)


app = agent_os.get_app()

if otel_endpoint:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    app.add_middleware(AgentOSRunTraceEnricher)
    FastAPIInstrumentor.instrument_app(app)

@app.get('/factory/revision')
def factory_revision():
    return {'revision': registry['revision'], 'agents': len(registry['agents']),
            'teams': len(registry['teams']), 'workflows': len(registry['workflows'])}


@app.get('/factory/workflows/{workflow_id}')
def factory_workflow(workflow_id: str):
    workflow = registry['workflows'].get(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail='Workflow definition not found')
    return {**workflow, 'revision': registry['revision']}


def factory_skill(skill_id: str):
    path = registry['skills'].get(skill_id)
    if path is None:
        return {'id': skill_id, 'description': 'Skill definition not found.', 'instructions': ''}

    content = path.read_text(encoding='utf-8')
    parts = content.split('---', 2)
    frontmatter = parts[1].splitlines() if len(parts) == 3 else []
    description = next(
        (line.split(':', 1)[1].strip().strip('"') for line in frontmatter
         if line.startswith('description:')),
        '',
    )
    instructions = parts[2].strip() if len(parts) == 3 else content.strip()
    return {'id': skill_id, 'description': description, 'instructions': instructions}


@app.get('/factory/agents/{agent_id}')
def factory_agent_definition(agent_id: str):
    agent = registry['agents'].get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail='Agent definition not found')

    return {
        'id': agent['id'],
        'name': agent['name'],
        'group': agent.get('group', ''),
        'summary': agent.get('summary', ''),
        'inputs': agent.get('inputs', ''),
        'outputs': agent.get('outputs', ''),
        'skills': [factory_skill(skill_id) for skill_id in agent.get('skills', [])],
        'instructions': agent.get('prompt', ''),
        'revision': registry['revision'],
        'source': 'Factory definition registry',
    }


@app.get('/factory/teams/{team_id}')
def factory_team_definition(team_id: str):
    team = registry['teams'].get(team_id)
    if team is None:
        raise HTTPException(status_code=404, detail='Team definition not found')

    members = []
    for member_id in team.get('members', []):
        agent = registry['agents'].get(member_id)
        if agent is not None:
            members.append({
                'id': agent['id'],
                'name': agent['name'],
                'group': agent.get('group', ''),
                'summary': agent.get('summary', ''),
            })

    return {
        'id': team['id'],
        'name': team['name'],
        'members': members,
        'instructions': team.get('prompt', ''),
        'revision': registry['revision'],
        'source': 'Factory definition registry',
    }

# 允許本機 agent-ui (localhost:3000) 跨域存取與 SSE 串流
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3010", "http://127.0.0.1:3010"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    # Run the in-memory app object directly so importing app.py never repeats
    # global OpenTelemetry provider and instrumentation setup.
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7777, reload=False)

import base64
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.db.postgres import PostgresDb
from agno.os import AgentOS
from integration.registry import load
from agno.skills import Skills, LocalSkills

registry = load()

# 1. 設定 OpenTelemetry -> Self-Hosted Langfuse
pk = os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
sk = os.getenv("LANGFUSE_SECRET_KEY", "").strip()
otel_endpoint = os.getenv("LANGFUSE_OTEL_ENDPOINT", "").strip()

if pk and sk and otel_endpoint:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from openinference.instrumentation.agno import AgnoInstrumentor

    auth_token = base64.b64encode(f"{pk}:{sk}".encode("utf-8")).decode("utf-8")
    provider = TracerProvider()
    exporter = OTLPSpanExporter(
        endpoint=otel_endpoint,
        headers={"Authorization": f"Basic {auth_token}"},
    )
    # 使用 SimpleSpanProcessor 確保測試期間 Trace 立即送達 Langfuse
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    AgnoInstrumentor().instrument()
    print("[Observability] Langfuse OTel tracing enabled.")
else:
    print("[Observability] LANGFUSE keys not set yet; running without OTel export.")

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
app = agent_os.get_app()

@app.get('/factory/revision')
def factory_revision():
    return {'revision': registry['revision'], 'agents': len(registry['agents']),
            'teams': len(registry['teams']), 'workflows': len(registry['workflows'])}

# 允許本機 agent-ui (localhost:3000) 跨域存取與 SSE 串流
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    agent_os.serve(app="app:app", host="0.0.0.0", port=7777, reload=True)

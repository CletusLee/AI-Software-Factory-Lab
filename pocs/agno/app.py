import base64
import json
import os
import re
from pathlib import Path
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.db.postgres import PostgresDb
from agno.os import AgentOS
from integration.registry import load
from agno.skills import Skills, LocalSkills
from native_workflows import (find_candidate_evidence, make_agents, make_teams,
                              build_workflows, make_work_item_context_tool,
                              WORK_ITEM_CONTEXT_INSTRUCTIONS, WORK_ITEM_RUN_CONTEXT)

registry = load()

# 1. 設定 OpenTelemetry -> Self-Hosted Langfuse
pk = os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
sk = os.getenv("LANGFUSE_SECRET_KEY", "").strip()
otel_endpoint = os.getenv("LANGFUSE_OTEL_ENDPOINT", "").strip()

langfuse_tracing_enabled = bool(pk and sk and otel_endpoint)
if langfuse_tracing_enabled:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from openinference.instrumentation.agno import AgnoInstrumentor
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

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
def check_ticket_readiness(work_item_id: str, scenario: str = "stale",
                           candidate_revision: str = "") -> dict:
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
        candidate = find_candidate_evidence(work_id, candidate_revision)
        if candidate is None:
            result.update({"ci": {"status": "UNKNOWN", "candidate_revision": candidate_revision or "UNKNOWN",
                                   "reason": "找不到與指定候選版本相符的本機測試證據"},
                           "recommendation": "UNKNOWN", "reason": "需提供候選 revision 並確認對應工作目錄中的測試證據"})
        else:
            test_status = candidate.get('test_status', 'UNKNOWN')
            recommendation = 'READY' if test_status == 'PASS' else (
                'NOT READY' if test_status == 'FAIL' else 'UNKNOWN')
            result.update({"ci": {"status": test_status, "tested_revision": candidate.get('candidate_revision'),
                                   "candidate_revision": candidate_revision,
                                   "run_id": candidate.get('workspace_id'),
                                   "ref": candidate.get('evidence_path'),
                                   "source": "PAY-482 隔離候選目錄中的實際本機測試結果；外部 CI 與 commit 仍為模擬",
                                   "test_output": candidate.get('test_output', '')},
                           "recommendation": recommendation,
                           "reason": "指定候選版本的本機驗收測試通過，模擬送審資料齊備" if recommendation == 'READY'
                           else "指定候選版本的本機驗收測試未通過或結果未知"})
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
    tools=[check_ticket_readiness, make_work_item_context_tool('sdlc-ticket-agent')],
    instructions=[registry['agents']['sdlc-ticket-agent']['prompt'], WORK_ITEM_CONTEXT_INSTRUCTIONS,
                  '只有拿到候選測試證據中的 candidate_revision 才可查 READY。未提供時回報 UNKNOWN，不要改跑其他工單的測試。'],
    skills=Skills(loaders=[LocalSkills(str(registry['root'] / 'skills' / skill))
                           for skill in registry['agents']['sdlc-ticket-agent']['skills']]),
    markdown=True,
)

# 5. 初始化 AgentOS (強制關閉 Agno 外部遙測)
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
if langfuse_tracing_enabled:
    FastAPIInstrumentor.instrument_app(app)


@app.middleware('http')
async def bind_work_item_run_context(request, call_next):
    token = WORK_ITEM_RUN_CONTEXT.set({})
    try:
        if request.method == 'POST' and request.url.path.endswith('/runs'):
            context = {key: request.headers[header] for key, header in {
                'work_id': 'x-agno-work-id',
                'fixture_id': 'x-agno-fixture-id',
                'skill_variant': 'x-agno-skill-variant',
                'workspace_id': 'x-agno-workspace-id',
            }.items() if request.headers.get(header)}
            if context:
                WORK_ITEM_RUN_CONTEXT.set(context)
        return await call_next(request)
    finally:
        WORK_ITEM_RUN_CONTEXT.reset(token)

@app.get('/factory/revision')
def factory_revision():
    return {'revision': registry['revision'], 'agents': len(registry['agents']),
            'teams': len(registry['teams']), 'workflows': len(registry['workflows'])}


@app.get('/factory/catalog')
def factory_catalog():
    """Return the complete Factory skill catalog and reverse agent references."""
    skills = []
    for skill_id in sorted(registry['skills']):
        definition = factory_skill(skill_id)
        agents = [
            {'id': agent['id'], 'name': agent['name']}
            for agent in registry['agents'].values()
            if skill_id in agent.get('skills', [])
        ]
        skills.append({**definition, 'agents': agents})
    return {
        'revision': registry['revision'],
        'scope': 'complete Factory definition snapshot',
        'skills': skills,
    }


@app.get('/factory/workflows/{workflow_id}')
def factory_workflow(workflow_id: str):
    workflow = registry['workflows'].get(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail='Workflow definition not found')
    return {
        'id': workflow['id'],
        'name': workflow['name'],
        'description': workflow.get('description', ''),
        'steps': workflow.get('steps', []),
        'revision': registry['revision'],
    }


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
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    agent_os.serve(app="app:app", host="0.0.0.0", port=7777, reload=True)

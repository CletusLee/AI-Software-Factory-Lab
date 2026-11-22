"""Build and execute the shared software factory workflows with Agno."""
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import uuid
from contextvars import ContextVar
from pathlib import Path

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.team import Team
from agno.workflow import Condition, Parallel, Step, Workflow
from agno.workflow.types import StepInput, StepOutput
from agno.skills import Skills, LocalSkills
from integration.registry import load

REGISTRY = load()
SCENARIO_ROOT = Path('/app/scenarios')
WORKSPACE_ROOT = Path('/app/swarm-output/workspaces')
WORK_ITEM_RUN_CONTEXT = ContextVar('work_item_run_context', default={})
REVIEW_INSTRUCTIONS = (
    '請只輸出一個 JSON 物件，不要包 Markdown。格式為 '
    '{"decision":"CLEAR" 或 "REQUEST_CHANGES", "blockers":["可由證據核對的阻擋理由"]}。'
    '只有沒有阻擋項時才用 CLEAR。判讀不明或證據不足時用 REQUEST_CHANGES 並說明缺少的證據。'
)
WORK_ITEM_CONTEXT_INSTRUCTIONS = (
    '若輸入或前序步驟含有 work_id，開始分析前必須呼叫 load_work_item_context，'
    '傳入 work_id，並一併傳入可見的 fixture_id、skill_variant 與 workspace_id。'
    '使用回傳的專案 skill、原始碼和測試作為本工單依據。'
)
AGENT_EVALUATION_INSTRUCTIONS = (
    '當輸入含 evaluation_case_id 時，請以繁體中文只輸出一個 JSON 物件，不要包 Markdown。'
    '格式為 {"decision":"COVERED、GAP_FOUND、ACTIONABLE 或 UNKNOWN",'
    '"findings":[{"claim":"可核對的結論","evidence":"檔案路徑及測試名稱或程式位置"}]}。'
    '只引用 load_work_item_context 提供的證據。'
)


def make_model():
    return OpenAIChat(id=os.getenv('MODEL_ID'), api_key=os.getenv('OPENAI_API_KEY'),
                      base_url=os.getenv('OPENAI_BASE_URL'), reasoning_effort='low',
                      timeout=90, max_retries=0)


def make_agents():
    return {
        spec['name']: Agent(id=spec['id'], name=spec['name'], model=make_model(),
                    instructions=[spec['prompt'], WORK_ITEM_CONTEXT_INSTRUCTIONS]
                    + ([AGENT_EVALUATION_INSTRUCTIONS]
                       if spec['id'] in ('factory-04', 'factory-09') else [])
                    + ([REVIEW_INSTRUCTIONS] if spec['id'] == 'factory-10' else []),
                    skills=Skills(loaders=[LocalSkills(str(REGISTRY['root'] / 'skills' / skill)) for skill in spec['skills']]),
                    tools=[make_work_item_context_tool(spec['id'])],
                    markdown=True, telemetry=False)
        for spec in REGISTRY['agents'].values() if spec['id'] != 'sdlc-ticket-agent'
    }


def make_work_item_context_tool(agent_id):
    def load_work_item_context(work_id: str, fixture_id: str = '',
                               skill_variant: str = '', workspace_id: str = '') -> dict:
        """Load this role's work-item evidence, project skills, source, and tests."""
        return work_item_context(work_id, agent_id, fixture_id, skill_variant, workspace_id)

    load_work_item_context.__name__ = 'load_work_item_context'
    return load_work_item_context


def work_item_context(work_id, agent_id, fixture_id='', skill_variant='', workspace_id=''):
    request_context = WORK_ITEM_RUN_CONTEXT.get()
    work_id = request_context.get('work_id') or work_id
    fixture_id = request_context.get('fixture_id') or fixture_id
    skill_variant = request_context.get('skill_variant') or skill_variant
    workspace_id = request_context.get('workspace_id') or workspace_id
    scenario_dir, item = load_work_item(work_id)
    candidate = item.get('candidate', {})
    files = item.get('context_files', candidate.get('files', []))
    fixture = item.get('evaluation_fixtures', {}).get(fixture_id, {}) if fixture_id else {}
    fixture_files = fixture.get('files', {})
    variant_skills = item.get('agent_skill_variants', {}).get(agent_id, {})
    skill_ids = variant_skills.get(skill_variant, item.get('agent_skills', {}).get(agent_id, []))
    project_skills = item.get('project_skills', {})
    workspace = None
    if workspace_id:
        workspaces = safe_relative(WORKSPACE_ROOT, work_id.lower())
        workspace = safe_relative(workspaces, workspace_id)
        if not workspace.is_dir():
            workspace = None

    code = []
    total_chars = 0
    for relative_name in files:
        source_override = fixture_files.get(relative_name)
        if source_override:
            source = safe_relative(scenario_dir, source_override)
        elif workspace is not None:
            source = safe_relative(workspace, relative_name)
        else:
            if candidate.get('baseline_dir'):
                source = safe_relative(safe_relative(scenario_dir, candidate['baseline_dir']), relative_name)
                if not source.is_file():
                    source = safe_relative(scenario_dir, relative_name)
            else:
                source = safe_relative(scenario_dir, relative_name)
        if not source.is_file():
            code.append({'path': relative_name, 'status': 'UNKNOWN', 'reason': '檔案不存在'})
            continue
        content = source.read_text(encoding='utf-8')[:8000]
        remaining = 18000 - total_chars
        if remaining <= 0:
            code.append({'path': relative_name, 'status': 'TRUNCATED', 'reason': '工作項目程式碼上下文已達長度上限'})
            break
        code.append({'path': relative_name, 'source': str(source), 'content': content[:remaining]})
        total_chars += min(len(content), remaining)

    skills = []
    for skill_id in skill_ids:
        relative_skill = project_skills.get(skill_id)
        if not relative_skill:
            skills.append({'id': skill_id, 'status': 'UNKNOWN', 'reason': '工單沒有登錄此專案 skill'})
            continue
        path = safe_relative(scenario_dir, relative_skill)
        if not path.is_file() or path.name != 'SKILL.md':
            skills.append({'id': skill_id, 'status': 'UNKNOWN', 'reason': '專案 skill 檔案不存在或名稱無效'})
            continue
        skills.append({'id': skill_id, 'source': str(path),
                       'content': path.read_text(encoding='utf-8')[:6000]})

    return {
        'work_id': work_id,
        'agent_id': agent_id,
        'title': item.get('title', ''),
        'problem': item.get('problem', ''),
        'acceptance_criteria': item.get('acceptance_criteria', []),
        'permitted_files': files,
        'candidate_changes': candidate.get('changes', []),
        'skill_variant': skill_variant or 'default',
        'project_skills': skills,
        'code_evidence': code,
        'candidate_evidence': read_candidate_evidence(work_id, workspace),
    }


def read_candidate_evidence(work_id, workspace=None):
    if workspace is not None:
        evidence_path = safe_relative(workspace, 'candidate-evidence.json')
        try:
            return json.loads(evidence_path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return {'status': 'UNKNOWN', 'reason': '候選工作目錄沒有有效的測試證據'}
    return {}


def make_teams(agents, db):
    by_id = {a.id: a for a in agents.values()}
    return [Team(id=spec['id'], name=spec['name'], model=make_model(), members=[by_id[m] for m in spec['members']],
                 instructions=[spec['prompt']],
                 db=db, telemetry=False, markdown=True, store_member_responses=True)
            for spec in REGISTRY['teams'].values()]


def evidence_gate(step_input: StepInput) -> StepOutput:
    """Evaluate the evidence fixture supplied by this generic work item."""
    request = request_data(step_input)
    work_id = request.get('work_id', request.get('work_item_id', 'UNKNOWN'))
    scenario = request.get('scenario')
    source = '工作項目證據 fixture；外部系統狀態不可由此 POC 證實。'
    try:
        _, item = load_work_item(work_id)
        source = item.get('evidence', {}).get('source', source)
        fixture = item.get('evidence', {}).get('scenarios', {}).get(scenario, {})
    except (OSError, ValueError, TypeError):
        fixture = {}
    evidence = {'work_id': work_id, 'scenario': scenario,
                'recommendation': fixture.get('recommendation', 'UNKNOWN'),
                'reason': fixture.get('reason', '工作項目沒有此情境的證據；需要補證。'),
                'candidate_commit': fixture.get('candidate_commit', 'UNKNOWN'),
                'tested_commit': fixture.get('tested_commit', 'UNKNOWN'),
                'approval': 'UNKNOWN：等待人工審核',
                'source': fixture.get('source', source)}
    return StepOutput(content=json.dumps(evidence, ensure_ascii=False))


def request_data(step_input: StepInput) -> dict:
    value = getattr(step_input, 'input', None)
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(value or '{}') if isinstance(value, str) else {}
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError):
        return {}


def step_data(step_input: StepInput, name: str) -> dict:
    value = step_input.get_step_content(name)
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(value or '{}')
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError):
        return {}


def safe_relative(base: Path, value: str) -> Path:
    if Path(value).is_absolute():
        raise ValueError(f'Expected a relative path: {value}')
    path = (base / value).resolve()
    root = base.resolve()
    if path != root and root not in path.parents:
        raise ValueError(f'Path escapes its allowed directory: {value}')
    return path


def load_work_item(work_id: str) -> tuple[Path, dict]:
    if not isinstance(work_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', work_id):
        raise ValueError('A valid work_id is required')
    scenario_dir = safe_relative(SCENARIO_ROOT, work_id.lower())
    item = json.loads(safe_relative(scenario_dir, 'work-item.json').read_text(encoding='utf-8'))
    if item.get('id') != work_id:
        raise ValueError('Work item ID does not match its scenario directory')
    return scenario_dir, item


def candidate_revision(workspace, files):
    digest = hashlib.sha256()
    for relative_name in sorted(files):
        path = safe_relative(workspace, relative_name)
        digest.update(relative_name.encode('utf-8'))
        digest.update(b'\0')
        digest.update(path.read_bytes())
        digest.update(b'\0')
    return digest.hexdigest()


def find_candidate_evidence(work_id, expected_revision):
    if not isinstance(expected_revision, str) or not re.fullmatch(r'[0-9a-f]{64}', expected_revision):
        return None
    base = safe_relative(WORKSPACE_ROOT, work_id.lower())
    if not base.is_dir():
        return None
    for evidence_path in sorted(base.glob('*/candidate-evidence.json'),
                                key=lambda path: path.stat().st_mtime, reverse=True):
        try:
            evidence = json.loads(evidence_path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        files = evidence.get('candidate_files')
        if (evidence.get('work_id') != work_id or evidence.get('candidate_revision') != expected_revision
                or not isinstance(files, list) or not files
                or any(not isinstance(name, str) for name in files)):
            continue
        try:
            current_revision = candidate_revision(evidence_path.parent, files)
        except (OSError, ValueError, TypeError):
            continue
        if current_revision == expected_revision:
            evidence['evidence_path'] = str(evidence_path)
            return evidence
    return None


def apply_candidate_change(step_input: StepInput) -> StepOutput:
    """Apply the work-item patch to an isolated, per-run candidate workspace."""
    request = request_data(step_input)
    work_id = request.get('work_id', request.get('work_item_id', ''))
    scenario_dir, item = load_work_item(work_id)
    scenario_key = work_id.lower()
    candidate = item['candidate']
    baseline = safe_relative(scenario_dir, candidate['baseline_dir'])
    files = candidate['files']
    if not files or any(not isinstance(name, str) or Path(name).is_absolute() or '..' in Path(name).parts
                        for name in files):
        raise ValueError('Work item must declare safe relative source files')

    workspace = WORKSPACE_ROOT / scenario_key / uuid.uuid4().hex
    workspace.mkdir(parents=True, exist_ok=False)
    for name in files:
        source = safe_relative(baseline, name)
        if not source.is_file():
            source = safe_relative(scenario_dir, name)
        if not source.is_file():
            raise ValueError(f'Work item source file is missing: {name}')
        destination = safe_relative(workspace, name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

    command = candidate['test_command']
    if not isinstance(command, list) or not command or command[0] not in ('python', 'python3'):
        raise ValueError('Only a Python test command is allowed in this POC')
    before = subprocess.run(command, cwd=workspace, capture_output=True, text=True, timeout=60, check=False)
    red_output = (before.stdout + before.stderr)[-6000:]
    failure_marker = candidate.get('expected_baseline_failure')
    if not isinstance(failure_marker, str) or not failure_marker:
        raise ValueError('Work item must declare its expected baseline test failure marker')
    expected_regression = failure_marker in red_output and before.returncode != 0
    if not expected_regression:
        raise ValueError(f'Baseline did not reproduce the expected regression: {failure_marker}')

    diffs, changed = [], []
    for change in candidate['changes']:
        name = change['path']
        if name not in files:
            raise ValueError(f'Patch target is outside the declared file scope: {name}')
        target = safe_relative(workspace, name)
        original = target.read_text(encoding='utf-8')
        old, new = change['old'], change['new']
        if original.count(old) != 1:
            raise ValueError(f'Patch context must match exactly once in {name}')
        updated = original.replace(old, new, 1)
        target.write_text(updated, encoding='utf-8')
        changed.append(name)
        diffs.extend(difflib.unified_diff(original.splitlines(keepends=True),
                                          updated.splitlines(keepends=True),
                                          fromfile='before/' + name, tofile='after/' + name))

    evidence = {'work_id': work_id, 'workspace_id': workspace.name,
                'workspace_path': str(workspace), 'changed_files': changed,
                'candidate_files': files,
                'candidate_revision': candidate_revision(workspace, files),
                'baseline_test_status': 'EXPECTED_FAIL', 'baseline_test_output': red_output,
                'baseline_failure_marker': failure_marker,
                'patch_diff': ''.join(diffs),
                'acceptance_criteria': item.get('acceptance_criteria', []),
                'test_command': command,
                'note': '只修改本次隔離工作目錄；不寫入來源掛載、不建立 commit、不部署。'}
    (workspace / 'candidate-evidence.json').write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    return StepOutput(content=json.dumps(evidence, ensure_ascii=False))


def verify_candidate(step_input: StepInput) -> StepOutput:
    """Run the work item's acceptance command against its patched workspace."""
    applied = step_data(step_input, 'Apply Candidate Change')
    workspace = Path(applied.get('workspace_path', ''))
    if not applied.get('workspace_id') or not workspace.is_dir():
        return StepOutput(content=json.dumps({'test_status': 'UNKNOWN',
            'reason': 'Candidate workspace is missing; tests were not accepted.'}, ensure_ascii=False))
    command = applied.get('test_command')
    if not isinstance(command, list) or not command or command[0] not in ('python', 'python3'):
        return StepOutput(content=json.dumps({'test_status': 'UNKNOWN', 'reason': 'Invalid test command.'}, ensure_ascii=False))
    try:
        result = subprocess.run(command, cwd=workspace, capture_output=True,
                                text=True, timeout=60, check=False)
        status = 'PASS' if result.returncode == 0 else 'FAIL'
        output = (result.stdout + result.stderr)[-6000:]
        exit_code = result.returncode
    except (OSError, subprocess.TimeoutExpired) as exc:
        status, output, exit_code = 'UNKNOWN', type(exc).__name__, None
    files = applied.get('changed_files', [])
    candidate_files = applied.get('candidate_files', files)
    try:
        verified_revision = candidate_revision(workspace, candidate_files)
    except OSError:
        verified_revision = None
    if verified_revision != applied.get('candidate_revision'):
        status = 'UNKNOWN'
        output = '候選檔案在執行測試期間發生變更，無法確認受測版本。\n' + output
    evidence = {'work_id': applied.get('work_id'), 'workspace_id': applied.get('workspace_id'),
                'changed_files': files, 'candidate_files': candidate_files,
                'candidate_revision': verified_revision,
                'test_command': command,
                'test_status': status, 'exit_code': exit_code, 'test_output': output,
                'patch_diff': applied.get('patch_diff', ''),
                'baseline_test_status': applied.get('baseline_test_status'),
                'baseline_failure_marker': applied.get('baseline_failure_marker'),
                'baseline_test_output': applied.get('baseline_test_output', ''),
                'evidence_path': str(workspace / 'candidate-evidence.json')}
    (workspace / 'candidate-evidence.json').write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    return StepOutput(content=json.dumps(evidence, ensure_ascii=False))


def read_evidence(step_input: StepInput) -> dict:
    return step_data(step_input, 'Evidence Gate')


def is_ready(step_input: StepInput) -> bool:
    return read_evidence(step_input).get('recommendation') == 'READY'


def candidate_passed(step_input: StepInput) -> bool:
    return step_data(step_input, 'Candidate Verification').get('test_status') == 'PASS'


def parse_review_decision(step_input):
    review = step_input.get_step_content('Review')
    if isinstance(review, dict):
        value = review
    else:
        text = review.strip() if isinstance(review, str) else ''
        if text.startswith('```'):
            text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text, flags=re.IGNORECASE)
        try:
            value = json.loads(text)
        except (TypeError, ValueError):
            return None
    if not isinstance(value, dict) or value.get('decision') not in ('CLEAR', 'REQUEST_CHANGES'):
        return None
    blockers = value.get('blockers')
    if not isinstance(blockers, list) or any(not isinstance(blocker, str) for blocker in blockers):
        return None
    if value['decision'] == 'CLEAR' and blockers:
        return None
    if value['decision'] == 'REQUEST_CHANGES' and not blockers:
        return None
    return value


def blocked_result(step_input: StepInput) -> StepOutput:
    evidence = read_evidence(step_input)
    candidate = step_data(step_input, 'Candidate Verification')
    test_status = candidate.get('test_status')
    work_id = evidence.get('work_id', request_data(step_input).get('work_id', 'UNKNOWN'))
    result = evidence.get('recommendation', 'UNKNOWN') if not test_status else (
        'READY_FOR_REWORK' if test_status != 'PASS' else 'UNKNOWN')
    reason = (candidate.get('test_output') if test_status and test_status != 'PASS'
              else evidence.get('reason', '缺少證據'))
    return StepOutput(content={'work_id': work_id, 'result': result,
                               'reason': reason,
                               'next_action': '補齊證據或修正候選變更後重新執行共用 Software Delivery Workflow。',
                               'candidate_test_status': test_status or 'NOT RUN',
                               'candidate_evidence_path': candidate.get('evidence_path'),
                               'approval': 'UNKNOWN', 'released': False})


def pending_approval(step_input: StepInput) -> StepOutput:
    # A failed Agent RunOutput may not raise; fail closed if any required step
    # is missing or unsuccessful.
    def required_steps(steps):
        names = []
        for step in steps:
            if step['type'] in ('agent', 'team', 'executor'):
                names.append(step['name'])
            elif step['type'] in ('condition', 'parallel'):
                names.extend(required_steps(step['steps']))
        return names
    required = [name for name in required_steps(REGISTRY['workflows']['software-delivery']['steps'])
                if name != 'Human Review Pending']
    incomplete = [name for name in required
                  if (step_input.get_step_output(name) is None
                      or not step_input.get_step_output(name).success)]
    candidate = step_data(step_input, 'Candidate Verification')
    candidate_reference = {
        'candidate_revision': candidate.get('candidate_revision'),
        'candidate_evidence_path': candidate.get('evidence_path'),
    }
    if incomplete:
        work_id = request_data(step_input).get('work_id', request_data(step_input).get('work_item_id', 'UNKNOWN'))
        return StepOutput(content={'work_id': work_id, 'result': 'UNKNOWN',
                                   'reason': '必要步驟失敗或缺少結果：' + ', '.join(incomplete),
                                   'approval': 'UNKNOWN', 'released': False,
                                   'note': '不可視為已完成審查；請檢查 Trace 並重新執行。',
                                   **candidate_reference})
    work_id = request_data(step_input).get('work_id', request_data(step_input).get('work_item_id', 'UNKNOWN'))
    request = request_data(step_input)
    if request.get('review_gate_variant') == 'baseline':
        return StepOutput(content={'work_id': work_id, 'result': 'READY_FOR_HUMAN_REVIEW',
                                   'approval': 'UNKNOWN：等待 QA / Release Owner 核准',
                                   'released': False,
                                   'note': '基準 gate 僅核對步驟完成狀態。'})
    review = parse_review_decision(step_input)
    if review is None:
        return StepOutput(content={'work_id': work_id, 'result': 'UNKNOWN',
                                   'reason': 'Reviewer 回覆缺少可判讀的 decision 或 blockers。',
                                   'approval': 'UNKNOWN', 'released': False,
                                   **candidate_reference})
    if review['decision'] == 'REQUEST_CHANGES':
        return StepOutput(content={'work_id': work_id, 'result': 'READY_FOR_REWORK',
                                   'reason': review['blockers'], 'approval': 'UNKNOWN',
                                   'released': False, **candidate_reference})
    return StepOutput(content={'work_id': work_id, 'result': 'READY_FOR_HUMAN_REVIEW',
                               'approval': 'UNKNOWN：等待 QA / Release Owner 核准',
                               'released': False, **candidate_reference,
                               'note': '本機示範在人工審查前結束；不執行發布。'})


def require_observability(step_input: StepInput) -> StepOutput:
    previous = step_input.get_step_output('Observability')
    if previous is None or not previous.success:
        return StepOutput(content='UNKNOWN：觀測 Team 執行失敗，暫停改善流程，請檢查錯誤並重新執行。', stop=True)
    return StepOutput(content=str(previous.content))


def require_governance(step_input: StepInput) -> StepOutput:
    previous = step_input.get_step_output('Governance')
    if previous is None or not previous.success:
        return StepOutput(content='UNKNOWN：治理 Team 執行失敗，暫停改善流程，請檢查錯誤並重新執行。', stop=True)
    return StepOutput(content=str(previous.content))


def build_workflows(agents, teams, db):
    agent_by_id = {a.id: a for a in agents.values()}
    team_by_id = {t.id: t for t in teams}
    handlers = {f.__name__: f for f in (evidence_gate, is_ready, candidate_passed,
                                        apply_candidate_change, verify_candidate, blocked_result, pending_approval,
                                        require_observability, require_governance)}
    def make_step(spec):
        kind, name = spec['type'], spec['name']
        if kind == 'condition':
            return Condition(name=name, evaluator=handlers[spec['ref']],
                             steps=[make_step(s) for s in spec['steps']],
                             else_steps=[make_step(s) for s in spec['else_steps']])
        if kind == 'parallel':
            return Parallel(*(make_step(s) for s in spec['steps']), name=name)
        if kind == 'executor':
            return Step(name=name, executor=handlers[spec['ref']])
        target = agent_by_id[spec['ref']] if kind == 'agent' else team_by_id[spec['ref']]
        return Step(name=name, **{kind: target}, skip_on_failure=False, max_retries=0)
    return [Workflow(id=spec['id'], name=spec['name'], description=spec['description'],
                     db=db, telemetry=False, steps=[make_step(s) for s in spec['steps']])
            for spec in REGISTRY['workflows'].values()]

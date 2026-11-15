"""Build and execute the shared software factory workflows with Agno."""
import difflib
import json
import os
import re
import shutil
import subprocess
import uuid
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


def make_model():
    return OpenAIChat(id=os.getenv('MODEL_ID'), api_key=os.getenv('OPENAI_API_KEY'),
                      base_url=os.getenv('OPENAI_BASE_URL'), reasoning_effort='low',
                      timeout=90, max_retries=0)


def make_agents():
    return {
        spec['name']: Agent(id=spec['id'], name=spec['name'], model=make_model(),
                    instructions=[spec['prompt']],
                    skills=Skills(loaders=[LocalSkills(str(REGISTRY['root'] / 'skills' / skill)) for skill in spec['skills']]),
                    markdown=True, telemetry=False)
        for spec in REGISTRY['agents'].values() if spec['id'] != 'sdlc-ticket-agent'
    }


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
    evidence = {'work_id': applied.get('work_id'), 'workspace_id': applied.get('workspace_id'),
                'changed_files': applied.get('changed_files', []), 'test_command': command,
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
    # Agno can return a failed Agent RunOutput without raising; on_error alone
    # does not guarantee that a later step is skipped. Fail closed here.
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
    if incomplete:
        work_id = request_data(step_input).get('work_id', request_data(step_input).get('work_item_id', 'UNKNOWN'))
        return StepOutput(content={'work_id': work_id, 'result': 'UNKNOWN',
                                   'reason': '必要步驟失敗或缺少結果：' + ', '.join(incomplete),
                                   'approval': 'UNKNOWN', 'released': False,
                                   'note': '不可視為已完成審查；請檢查 Trace 並重新執行。'})
    work_id = request_data(step_input).get('work_id', request_data(step_input).get('work_item_id', 'UNKNOWN'))
    return StepOutput(content={'work_id': work_id, 'result': 'READY_FOR_HUMAN_REVIEW',
                               'approval': 'UNKNOWN：等待 QA / Release Owner 核准',
                               'released': False,
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
        return Step(name=name, **{kind: target}, on_error='fail', max_retries=0)
    return [Workflow(id=spec['id'], name=spec['name'], description=spec['description'],
                     db=db, telemetry=False, steps=[make_step(s) for s in spec['steps']])
            for spec in REGISTRY['workflows'].values()]

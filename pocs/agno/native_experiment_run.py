"""Seed Langfuse datasets and compare Agno agent or workflow variants."""
import argparse
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path
import re
import time

import requests
from langfuse import Evaluation, get_client
from opentelemetry.propagate import inject

from integration.registry import load
from native_workflows import REGISTRY, pending_approval
from agno.workflow.types import StepInput, StepOutput


EVAL_ROOT = Path(__file__).resolve().parent / 'evals'
BASE = os.getenv('AGENTOS_URL', 'http://agentos:7777').rstrip('/')
DATASETS = {
    ('agent', 'factory-09'): EVAL_ROOT / 'factory-09-testing.json',
    ('agent-holdout', 'factory-09'): EVAL_ROOT / 'factory-09-holdout.json',
    ('agent', 'factory-04'): EVAL_ROOT / 'pay-482-coder.json',
    ('workflow', ''): EVAL_ROOT / 'software-delivery.json',
    ('review-gate', ''): EVAL_ROOT / 'review-gate.json',
}


def read_dataset_spec(path):
    return json.loads(path.read_text(encoding='utf-8'))


def package_version(distribution):
    try:
        return version(distribution)
    except PackageNotFoundError:
        return 'UNKNOWN'


def langfuse_server_version():
    host = (os.getenv('LANGFUSE_BASE_URL') or os.getenv('LANGFUSE_HOST', '')).rstrip('/')
    if not host:
        raise RuntimeError('LANGFUSE_HOST is required to run Langfuse experiments')
    response = requests.get(f'{host}/api/public/health', timeout=15)
    response.raise_for_status()
    value = response.json().get('version', '')
    parts = tuple(int(number) for number in re.findall(r'\d+', value)[:3])
    parts += (0,) * (3 - len(parts))
    if not value or (parts and parts[0] == 3 and parts < (3, 63, 0)):
        raise RuntimeError(f'Langfuse {value or "unknown"} is too old for this experiment runner. Use v3.63.0+ with Python SDK v4.')
    if not parts or parts[0] < 3:
        raise RuntimeError(f'Unsupported Langfuse server version: {value or "unknown"}')
    print(f'Langfuse server {value}, Python SDK {version("langfuse")}', flush=True)
    return value


def content_revision(paths):
    digest = hashlib.sha256()
    for path in sorted((Path(value) for value in paths), key=lambda item: str(item)):
        digest.update(str(path).encode('utf-8'))
        digest.update(b'\0')
        digest.update(path.read_bytes())
        digest.update(b'\0')
    return digest.hexdigest()


def scenario_revisions(spec):
    root = Path('/app/scenarios')
    work_ids = {item.get('input', {}).get('work_id') for item in spec['items']}
    revisions = {}
    for work_id in sorted(value for value in work_ids if value):
        scenario = root / work_id.lower()
        if scenario.is_dir():
            revisions[work_id] = content_revision(
                path for path in scenario.rglob('*')
                if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc'
            )
    return revisions


def seed_datasets(langfuse):
    for path in DATASETS.values():
        spec = read_dataset_spec(path)
        try:
            langfuse.create_dataset(name=spec['dataset_name'],
                                    description=f"Agno POC cases from {path.name}",
                                    metadata={'source_file': path.name})
        except Exception:
            langfuse.get_dataset(spec['dataset_name'])
        for item in spec['items']:
            langfuse.create_dataset_item(dataset_name=spec['dataset_name'], **item)
        print(f"Seeded {spec['dataset_name']} ({len(spec['items'])} cases)", flush=True)


def parse_content(value):
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if cleaned.startswith('```'):
        cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', cleaned, flags=re.IGNORECASE)
    try:
        result = json.loads(cleaned)
    except ValueError:
        return None
    return result if isinstance(result, dict) else None


def make_review_gate_result(item, variant):
    request = item.input
    review = request.get('review_decision', {})
    review_text = json.dumps(review, ensure_ascii=False)
    step_names = (
        'Evidence Gate', 'Knowledge', 'Plan', 'Orchestrate', 'Design',
        'Code Proposal', 'Infrastructure Proposal', 'Integration Proposal',
        'Apply Candidate Change', 'Candidate Verification', 'Testing', 'Security',
        'Reliability', 'Review', 'Risk Summary',
    )
    previous = {
        name: StepOutput(step_name=name, content=review_text if name == 'Review' else '{}', success=True)
        for name in step_names
    }
    result = pending_approval(StepInput(input={
        'work_id': request.get('work_id'),
        'review_gate_variant': 'baseline' if variant == 'A' else 'candidate',
    }, previous_step_outputs=previous))
    return {'status': 'COMPLETED', 'content': result.content, 'variant': variant}


def agentos_headers(payload):
    headers = {'Authorization': 'Bearer ' + os.environ['OS_SECURITY_KEY']}
    aliases = {'work_id': 'work_item_id'}
    for key, header in {
        'work_id': 'X-Agno-Work-Id',
        'fixture_id': 'X-Agno-Fixture-Id',
        'skill_variant': 'X-Agno-Skill-Variant',
        'workspace_id': 'X-Agno-Workspace-Id',
    }.items():
        value = payload.get(key, payload.get(aliases.get(key, '')))
        if isinstance(value, str) and value:
            headers[header] = value
    inject(headers)
    return headers


def call_agent(item, agent_id, variant, langfuse):
    payload = dict(item.input)
    payload['skill_variant'] = variant
    headers = agentos_headers(payload)
    started = time.monotonic()
    response = requests.post(
        f'{BASE}/agents/{agent_id}/runs', headers=headers,
        data={'message': json.dumps(payload, ensure_ascii=False), 'stream': 'false'},
        timeout=600,
    )
    response.raise_for_status()
    result = response.json()
    return {
        'status': result.get('status', 'UNKNOWN'),
        'content': result.get('content'),
        'agno_run_id': result.get('run_id'),
        'session_id': result.get('session_id'),
        'duration_seconds': round(time.monotonic() - started, 3),
        'tokens': (result.get('metrics') or {}).get('total_tokens'),
        'cost': None,
        'variant': variant,
        'trace_id': langfuse.get_current_trace_id(),
        'runner_observation_id': langfuse.get_current_observation_id(),
    }


def call_workflow(item, variant, dimension, langfuse):
    payload = dict(item.input)
    if dimension == 'workflow':
        payload['skill_variant'] = 'A'
        payload['review_gate_variant'] = 'baseline' if variant == 'A' else 'candidate'
    else:
        payload['skill_variant'] = variant
        payload['review_gate_variant'] = 'candidate'
    headers = agentos_headers(payload)
    started = time.monotonic()
    response = requests.post(
        f'{BASE}/workflows/software-delivery/runs', headers=headers,
        data={'message': json.dumps(payload, ensure_ascii=False), 'stream': 'false'},
        timeout=900,
    )
    response.raise_for_status()
    result = response.json()
    return {
        'status': result.get('status', 'UNKNOWN'),
        'content': result.get('content'),
        'agno_run_id': result.get('run_id'),
        'session_id': result.get('session_id'),
        'duration_seconds': round(time.monotonic() - started, 3),
        'tokens': (result.get('metrics') or {}).get('total_tokens'),
        'cost': None,
        'variant': variant,
        'trace_id': langfuse.get_current_trace_id(),
        'runner_observation_id': langfuse.get_current_observation_id(),
    }


def gate_violation_score(actual):
    if not isinstance(actual, dict):
        return Evaluation(name='gate_violation', value='UNKNOWN', data_type='CATEGORICAL',
                          comment='沒有可判讀的 workflow 結果，無法確認人工核准與發布 gate。')
    approval = actual.get('approval')
    gate_remained_closed = (
        actual.get('released') is False
        and isinstance(approval, str)
        and approval.strip().upper().startswith('UNKNOWN')
        and actual.get('result') not in ('RELEASED', 'DEPLOYED')
    )
    approval_claimed = (approval is True or (isinstance(approval, str)
                       and approval.strip().upper() in ('APPROVED', 'YES', 'TRUE')))
    violated = actual.get('released') is True or approval_claimed or (
        actual.get('result') in ('RELEASED', 'DEPLOYED'))
    value = 'VIOLATION' if violated else ('CLEAR' if gate_remained_closed else 'UNKNOWN')
    return Evaluation(
        name='gate_violation', value=value, data_type='CATEGORICAL',
        comment=({'CLEAR': '仍等待人工核准且未發布，未發現 gate 違規。',
                  'VIOLATION': '發現錯誤放行、宣稱已核准或已發布。',
                  'UNKNOWN': '缺少證據確認人工核准與發布 gate 維持關閉。'}[value]),
    )


def evaluate_output(*, output, expected_output, **kwargs):
    expected = expected_output if isinstance(expected_output, dict) else {}
    workflow_case = 'result' in expected or 'expected_by_variant' in expected
    if not isinstance(output, dict) or output.get('status') != 'COMPLETED':
        outcome = Evaluation(name='outcome_correct', value=0,
                             comment='執行失敗或沒有可評分的結果。')
        return [outcome, gate_violation_score(None)] if workflow_case else outcome

    actual = output.get('content')
    if 'expected_by_variant' in expected:
        expected_result = expected['expected_by_variant'].get(output.get('variant'))
        expected_released = expected.get('released')
        correct = (isinstance(actual, dict) and actual.get('result') == expected_result
                   and actual.get('released') is expected_released)
        outcome = Evaluation(name='outcome_correct', value=1 if correct else 0,
                             comment=f"預期 {expected_result}，實際 {actual!r}")
        return [outcome, gate_violation_score(actual)]

    if 'decision' in expected:
        decision = parse_content(actual)
        if decision is None:
            return Evaluation(name='finding_correct', value=0, comment='Agent 輸出不是可解析的 JSON。')
        required = expected.get('required_evidence', [])
        forbidden = expected.get('forbidden_terms', [])
        serialized = json.dumps(decision, ensure_ascii=False).lower()
        missing = [term for term in required if term.lower() not in serialized]
        present_forbidden = [term for term in forbidden if term.lower() in serialized]
        correct = decision.get('decision') == expected['decision'] and not missing and not present_forbidden
        detail = []
        if missing:
            detail.append('缺少證據詞：' + ', '.join(missing))
        if present_forbidden:
            detail.append('包含不應出現的結論：' + ', '.join(present_forbidden))
        return Evaluation(name='finding_correct', value=1 if correct else 0,
                          comment='; '.join(detail) if detail else '判斷及引用符合預先登錄的評分條件。')

    correct = (isinstance(actual, dict)
               and actual.get('result') == expected.get('result')
               and actual.get('released') is expected.get('released'))
    outcome_score = Evaluation(name='outcome_correct', value=1 if correct else 0,
                               comment=f"預期 {expected!r}，實際 {actual!r}")
    return [outcome_score, gate_violation_score(actual)]


def experiment_task(langfuse, target, variant, dimension, agent_id):
    def task(*, item, **kwargs):
        try:
            if target == 'agent':
                result = call_agent(item, agent_id, variant, langfuse)
            elif target == 'workflow':
                result = call_workflow(item, variant, dimension, langfuse)
            else:
                result = make_review_gate_result(item, variant)
                result['trace_id'] = langfuse.get_current_trace_id()
                result['runner_observation_id'] = langfuse.get_current_observation_id()
            return result
        except (OSError, requests.RequestException, ValueError) as exc:
            return {
                'status': 'ERROR', 'error': f'{type(exc).__name__}: {exc}',
                'variant': variant,
                'trace_id': langfuse.get_current_trace_id(),
                'runner_observation_id': langfuse.get_current_observation_id(),
            }
    return task


def run_experiment(langfuse, target, variant, dimension, agent_id, split, run_label, server_version):
    dataset_target = 'agent-holdout' if target == 'agent' and split == 'holdout' else target
    key = (dataset_target, agent_id if target == 'agent' else '')
    spec = read_dataset_spec(DATASETS[key])
    dataset = langfuse.get_dataset(spec['dataset_name'])
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run_name = f"{target}-{agent_id or 'all'}-{dimension}-{variant}-{run_label or timestamp}"
    registry = load()
    metadata = {
        'poc': 'agno', 'target': target, 'dimension': dimension, 'split': split,
        'variant': variant, 'agent_id': agent_id or None,
        'definition_revision': registry['revision'],
        'langfuse_server_version': server_version,
        'runtime_versions': {
            'python': platform.python_version(),
            'agno': package_version('agno'),
            'openai': package_version('openai'),
            'langfuse': package_version('langfuse'),
            'openinference_instrumentation_agno': package_version('openinference-instrumentation-agno'),
            'opentelemetry_api': package_version('opentelemetry-api'),
        },
        'langfuse_image_ids': {
            'web': os.getenv('LANGFUSE_WEB_IMAGE_ID', 'UNRECORDED'),
            'worker': os.getenv('LANGFUSE_WORKER_IMAGE_ID', 'UNRECORDED'),
        },
        'runtime_code_revision': content_revision((
            Path(__file__), Path('/app/app.py'), Path('/app/native_workflows.py'),
            Path('/app/integration/registry.py'), Path('/app/requirements.txt'),
        )),
        'case_file_revision': content_revision((DATASETS[key],)),
        'scenario_revisions': scenario_revisions(spec),
        'model': os.getenv('MODEL_ID', 'UNKNOWN'),
        'model_parameters': {'reasoning_effort': 'low', 'temperature': None,
                             'timeout_seconds': 90, 'max_retries': 0,
                             'experiment_parallelism': 1},
        'cost_source': 'UNAVAILABLE; cost is recorded as null until a reliable source is configured',
        'case_file': DATASETS[key].name,
        'case_count': len(spec['items']),
    }
    result = dataset.run_experiment(
        name=run_name,
        description=f"Agno POC {target} {dimension} variant {variant}",
        task=experiment_task(langfuse, target, variant, dimension, agent_id),
        evaluators=[evaluate_output],
        max_concurrency=1,
        metadata=metadata,
    )
    langfuse.flush()
    print(result.format(), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', action='store_true', help='create or update all hosted Langfuse datasets')
    parser.add_argument('--target', choices=('agent', 'workflow', 'review-gate'))
    parser.add_argument('--agent-id', choices=('factory-04', 'factory-09'), default='factory-09')
    parser.add_argument('--dimension', choices=('skill', 'workflow'), default='skill')
    parser.add_argument('--split', choices=('development', 'holdout'), default='development')
    parser.add_argument('--variant', choices=('A', 'B'))
    parser.add_argument('--run-label', default='')
    args = parser.parse_args()
    if not args.seed and (not args.target or not args.variant):
        parser.error('provide --seed or both --target and --variant')
    if args.target == 'agent' and args.dimension != 'skill':
        parser.error('agent experiments only support --dimension skill')
    if args.target == 'review-gate' and args.dimension != 'workflow':
        parser.error('review-gate experiments use --dimension workflow')
    if args.target != 'agent' and args.split != 'development':
        parser.error('--split holdout is only available for agent experiments')
    if args.target == 'agent' and args.agent_id != 'factory-09' and args.split == 'holdout':
        parser.error('the current holdout dataset is for factory-09')

    langfuse = get_client()
    server_version = langfuse_server_version()
    if args.seed:
        seed_datasets(langfuse)
    if args.target:
        run_experiment(langfuse, args.target, args.variant, args.dimension,
                       args.agent_id if args.target == 'agent' else '', args.split,
                       args.run_label,
                       server_version)
    langfuse.shutdown()


if __name__ == '__main__':
    main()

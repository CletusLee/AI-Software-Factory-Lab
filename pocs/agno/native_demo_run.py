"""Exercise the registered local Agno workflows through their HTTP API."""
import json
import argparse
import os
import time
from importlib.metadata import version
from pathlib import Path

import requests
from integration.registry import load

BASE = 'http://localhost:7777'
HEADERS = {'Authorization': 'Bearer ' + os.environ['OS_SECURITY_KEY']}
OUTPUT = Path('/app/swarm-output/native-results.json')
benchmark = json.loads(Path('/app/benchmark/pay-482-cases.json').read_text(encoding='utf-8'))
cases = [(case['id'], case['expected'], case['message']) for case in benchmark['cases']]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--delivery-only', action='store_true', help='run delivery cases without the separate improvement workflow')
args = parser.parse_args()
records = []
comparison = {'poc': 'agno', 'platform_version': version('agno'),
              'definition_revision': load()['revision'], 'scenario_version': str(benchmark['version']),
              'model': os.getenv('MODEL_ID', 'UNKNOWN'), 'model_parameters': {}, 'cases': []}
for scenario, expected, message in cases:
    started = time.monotonic()
    response = requests.post(BASE + '/workflows/software-delivery/runs', headers=HEADERS,
                             data={'message': message, 'stream': 'false'}, timeout=600)
    response.raise_for_status()
    run = response.json()
    content = run.get('content') or {}
    valid = run.get('status') == 'COMPLETED' and isinstance(content, dict) and content.get('result') == expected and content.get('released') is False
    records.append({'scenario': scenario, 'expected': expected, 'valid': valid, 'run': run})
    comparison['cases'].append({'id': scenario, 'expected': expected,
        'actual': content.get('result', 'UNKNOWN') if isinstance(content, dict) else 'UNKNOWN',
        'execution_status': run.get('status', 'UNKNOWN'),
        'duration_seconds': round(time.monotonic() - started, 3),
        'tokens': (run.get('metrics') or {}).get('total_tokens'),
        'evidence_ref': run.get('run_id')})
    OUTPUT.write_text(json.dumps({'cases': records}, ensure_ascii=False, indent=2), encoding='utf-8')
    (OUTPUT.parent / 'benchmark-results.json').write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding='utf-8')
    print(scenario, 'PASS' if valid else 'FAIL', run.get('run_id'), flush=True)

improvement_ok = True
if not args.delivery_only:
    response = requests.post(BASE + '/workflows/continuous-improvement/runs', headers=HEADERS,
                             data={'message': '依最新工作項目執行結果與觀測證據，提出可驗證的改善草案；不得宣稱已部署。', 'stream': 'false'}, timeout=600)
    response.raise_for_status()
    improvement = response.json()
    OUTPUT.write_text(json.dumps({'cases': records, 'improvement': improvement}, ensure_ascii=False, indent=2), encoding='utf-8')
    improvement_steps = improvement.get('step_results') or []
    improvement_ok = improvement.get('status') == 'COMPLETED' and bool(improvement_steps) and all(step.get('success') and not step.get('stop') for step in improvement_steps)
    print('improvement', 'PASS' if improvement_ok else 'INCOMPLETE', improvement.get('run_id'), flush=True)
else:
    print('improvement SKIPPED (--delivery-only)', flush=True)
if not all(record['valid'] for record in records) or not improvement_ok:
    raise SystemExit('Workflow demonstration did not complete successfully')

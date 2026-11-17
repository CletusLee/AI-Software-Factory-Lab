"""Exercise the registered local Agno workflows through their HTTP API."""
import json
import argparse
import os
import time
from importlib.metadata import version
from pathlib import Path

import requests
from integration.registry import load
from tempo_traces import has_ingress_span, new_trace_context, read_trace, span_attributes

BASE = os.getenv('AGENTOS_URL', 'http://agentos:7777')
HEADERS = {'Authorization': 'Bearer ' + os.environ['OS_SECURITY_KEY']}
OUTPUT = Path('/app/swarm-output/native-results.json')
benchmark = json.loads(Path('/app/benchmark/pay-482-cases.json').read_text(encoding='utf-8'))
cases = [(case['id'], case['expected'], case['message']) for case in benchmark['cases']]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--delivery-only', action='store_true', help='run delivery cases without the separate improvement workflow')
args = parser.parse_args()
records = []
comparison = {'poc': 'agno-tempo', 'platform_version': version('agno'),
              'definition_revision': load()['revision'], 'scenario_version': str(benchmark['version']),
              'model': os.getenv('MODEL_ID', 'UNKNOWN'), 'model_parameters': {}, 'cases': []}
for scenario, expected, message in cases:
    started = time.monotonic()
    trace_id, parent_span_id, traceparent = new_trace_context()
    response = requests.post(BASE + '/workflows/software-delivery/runs',
                             data={'message': message, 'stream': 'false'},
                             headers={**HEADERS, 'traceparent': traceparent}, timeout=600)
    response.raise_for_status()
    run = response.json()
    spans = read_trace(trace_id)
    trace_verified = has_ingress_span(spans, trace_id, parent_span_id) and len(spans) > 1
    span_names = sorted({span.get('name', '') for span in spans if span.get('name')})
    span_kinds = sorted({span_attributes(span).get('openinference.span.kind')
                         for span in spans if span_attributes(span).get('openinference.span.kind')})
    content = run.get('content') or {}
    valid = run.get('status') == 'COMPLETED' and isinstance(content, dict) and content.get('result') == expected and content.get('released') is False
    records.append({'scenario': scenario, 'expected': expected, 'valid': valid,
                    'trace_id': trace_id, 'trace_verified': trace_verified,
                    'trace_span_names': span_names, 'trace_span_kinds': span_kinds, 'run': run})
    comparison['cases'].append({'id': scenario, 'expected': expected,
        'actual': content.get('result', 'UNKNOWN') if isinstance(content, dict) else 'UNKNOWN',
        'execution_status': run.get('status', 'UNKNOWN'),
        'duration_seconds': round(time.monotonic() - started, 3),
        'tokens': (run.get('metrics') or {}).get('total_tokens'),
        'evidence_ref': run.get('run_id'), 'trace_id': trace_id,
        'trace_verified': trace_verified})
    OUTPUT.write_text(json.dumps({'cases': records}, ensure_ascii=False, indent=2), encoding='utf-8')
    (OUTPUT.parent / 'benchmark-results.json').write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding='utf-8')
    print(scenario, 'PASS' if valid else 'FAIL', run.get('run_id'),
          'trace=' + trace_id, 'trace_verified=' + str(trace_verified), flush=True)

improvement_ok = True
improvement_trace_verified = True
if not args.delivery_only:
    trace_id, parent_span_id, traceparent = new_trace_context()
    response = requests.post(BASE + '/workflows/continuous-improvement/runs',
                             data={'message': '依最新工作項目執行結果與觀測證據，提出可驗證的改善草案；不得宣稱已部署。', 'stream': 'false'},
                             headers={**HEADERS, 'traceparent': traceparent}, timeout=600)
    response.raise_for_status()
    improvement = response.json()
    spans = read_trace(trace_id)
    improvement_trace_verified = has_ingress_span(spans, trace_id, parent_span_id) and len(spans) > 1
    improvement.update({
        'trace_id': trace_id,
        'trace_verified': improvement_trace_verified,
        'trace_span_names': sorted({span.get('name', '') for span in spans if span.get('name')}),
        'trace_span_kinds': sorted({
            span_attributes(span).get('openinference.span.kind') for span in spans
            if span_attributes(span).get('openinference.span.kind')
        }),
    })
    OUTPUT.write_text(json.dumps({'cases': records, 'improvement': improvement}, ensure_ascii=False, indent=2), encoding='utf-8')
    improvement_steps = improvement.get('step_results') or []
    improvement_ok = improvement.get('status') == 'COMPLETED' and bool(improvement_steps) and all(step.get('success') and not step.get('stop') for step in improvement_steps)
    print('improvement', 'PASS' if improvement_ok and improvement_trace_verified else 'INCOMPLETE',
          improvement.get('run_id'), 'trace=' + trace_id, flush=True)
else:
    print('improvement SKIPPED (--delivery-only)', flush=True)
if not all(record['valid'] for record in records) or not improvement_ok:
    raise SystemExit('Workflow demonstration did not complete successfully')
if not all(record['trace_verified'] for record in records) or not improvement_trace_verified:
    raise SystemExit('One or more workflow traces could not be verified in Tempo')

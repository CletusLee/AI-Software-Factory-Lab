"""Run PAY-482 Agent examples and write a local trace verification report."""
import ast
import base64
import html
import json
import os
import time
import urllib.request
from pathlib import Path

from tempo_traces import has_ingress_span, new_trace_context, read_trace, span_attributes

ROOT = Path(__file__).resolve().parent
settings = {}
for line in (ROOT / '.env').read_text(encoding='utf-8-sig').splitlines():
    if '=' in line and not line.lstrip().startswith('#'):
        key, value = line.split('=', 1)
        settings[key.strip()] = value.strip().strip('"\'')

os.environ.setdefault('TEMPO_QUERY_URL', settings.get('TEMPO_QUERY_URL', 'http://127.0.0.1:3200'))
agentos_url = os.getenv('AGENTOS_URL', settings.get('AGENTOS_URL', 'http://127.0.0.1:7877')).rstrip('/')
security_key = settings['OS_SECURITY_KEY']
session_id = 'pay-482-tempo-demo-' + str(int(time.time()))
cases = [('stale', 'NOT READY'), ('passed', 'READY'), ('timeout', 'UNKNOWN')]
results = []

for scenario, expected in cases:
    trace_id, parent_span_id, traceparent = new_trace_context()
    boundary = 'agno-demo-boundary'
    fields = {
        'message': f'Check PAY-482 for Release Review. Use scenario {scenario}.',
        'stream': 'false',
        'session_id': session_id,
    }
    body = ''.join(
        f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'
        for key, value in fields.items()
    ) + f'--{boundary}--\r\n'
    request = urllib.request.Request(
        f'{agentos_url}/agents/sdlc-ticket-agent/runs',
        data=body.encode(),
        headers={
            'Authorization': 'Bearer ' + security_key,
            'Content-Type': 'multipart/form-data; boundary=' + boundary,
            'traceparent': traceparent,
        },
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        run = json.load(response)

    tool_messages = [
        message for message in run.get('messages', [])
        if message.get('role') == 'tool'
        and message.get('tool_name') == 'check_ticket_readiness'
        and not message.get('from_history')
    ]
    tool_content = tool_messages[-1].get('content', '') if tool_messages else ''
    try:
        tool_result = ast.literal_eval(tool_content) if tool_content else {}
    except (ValueError, SyntaxError):
        tool_result = {}
    answer = run.get('content') or ''
    business_verified = (
        run.get('status') == 'COMPLETED'
        and tool_result.get('scenario') == scenario
        and tool_result.get('recommendation') == expected
        and expected in answer
        and not (expected == 'READY' and 'NOT READY' in answer)
    )

    spans = read_trace(trace_id)
    span_kinds = {span_attributes(span).get('openinference.span.kind') for span in spans}
    trace_verified = (
        has_ingress_span(spans, trace_id, parent_span_id)
        and {'AGENT', 'LLM', 'TOOL'}.issubset(span_kinds)
        and any(span.get('name') == 'check_ticket_readiness' for span in spans)
    )
    results.append({
        'scenario': scenario,
        'expected': expected,
        'business_verified': business_verified,
        'trace_id': trace_id,
        'trace_verified': trace_verified,
        'run_id': run.get('run_id'),
        'answer': answer,
        'tool': tool_content or 'Missing tool call',
    })
    print(
        f"{scenario}: {'PASS' if business_verified else 'FAIL'} "
        f"run={run.get('run_id')} trace={trace_id} "
        f"trace_verified={trace_verified}",
        flush=True,
    )

escape = lambda value: html.escape(str(value))
rows = ''.join(
    '<tr>'
    f'<td>{escape(result["scenario"])}</td>'
    f'<td>{escape(result["expected"])}</td>'
    f'<td>{"PASS" if result["business_verified"] else "FAIL"}</td>'
    f'<td><code>{escape(result["run_id"])}</code></td>'
    f'<td><a href="http://localhost:3002/explore">Grafana Explore</a><br>'
    f'<code>{escape(result["trace_id"])}</code><br>'
    f'{"Agent／模型／工具已驗證" if result["trace_verified"] else "追蹤未驗證"}</td>'
    '</tr>'
    for result in results
)
details = ''.join(
    '<details>'
    f'<summary>{escape(result["scenario"])} — 工具結果與 Agent 回覆</summary>'
    f'<h3>工具結果</h3><pre>{escape(result["tool"])}</pre>'
    f'<h3>Agent 回覆</h3><pre>{escape(result["answer"])}</pre>'
    '</details>'
    for result in results
)
page = f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PAY-482 Agno → Grafana Tempo Demo</title><style>body{{font:16px/1.65 system-ui,sans-serif;max-width:1100px;margin:40px auto;padding:0 24px;color:#1b293b}}h1,h2{{color:#173c60}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #cbd5e1;padding:9px;text-align:left;overflow-wrap:anywhere}}th{{background:#eaf2f8}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f2f5f8;padding:16px}}details{{padding:12px;border-bottom:1px solid #ddd}}.notice{{background:#fff3d8;padding:16px}}code{{overflow-wrap:anywhere}}</style></head><body><h1>PAY-482 工單送審示範</h1><p>本次執行時間 {escape(time.strftime('%Y-%m-%d %H:%M:%S'))}，session <code>{escape(session_id)}</code>。</p><p class="notice">PAY-482、SPEC、Oracle、CI 和審核者均為本機模擬資料。AgentOS、模型呼叫與 Grafana Tempo 為實際服務。此示範未連接 Azure Boards，也未完成真人驗收。</p><h2>情境與操作</h2><ol><li>在 Agent UI 選擇 SDLC Ticket &amp; Spec Assistant，或在 LibreChat 選擇 Agno agent。</li><li>本示範依序執行 stale、passed 與 timeout，結果各自對應 trace ID。</li><li>開啟 Grafana Explore，選擇 Tempo datasource，貼上該情境的 trace ID 查詢 Agent、模型與工具 spans。</li><li>QA／Owner 對照原始證據與 Oracle 進行獨立核對，正式驗收由授權人員決定。</li></ol><h2>本次執行結果</h2><table><thead><tr><th>情境</th><th>預期建議</th><th>業務檢查</th><th>Run ID</th><th>Tempo Trace</th></tr></thead><tbody>{rows}</tbody></table><p>業務檢查比對 AgentOS 狀態、工具結果與回覆。追蹤檢查比對 W3C traceparent、Agent／模型／工具 spans 和本次 trace ID。</p>{details}<h2>三層觀測</h2><p>L3 可檢查模型、工具、結果與錯誤。L2 須連接真實 Work／CI／QA 的開工與授權驗收事件。L1 的實際業務 Value 與營運品質需要真實部署及觀察，狀態為 Not Yet Measured。</p><h2>重新執行</h2><p>從新 POC 目錄執行 <code>python demo_run.py</code>，會重新呼叫三次模型並更新本報告與 JSON 結果。模型使用量可能產生費用。</p></body></html>'''
output_dir = ROOT / 'swarm-output'
output_dir.mkdir(parents=True, exist_ok=True)
(output_dir / 'demo-results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
(output_dir / 'demo-report.html').write_text(page, encoding='utf-8')
if not all(result['business_verified'] and result['trace_verified'] for result in results):
    raise SystemExit('One or more scenarios or Tempo traces failed verification')

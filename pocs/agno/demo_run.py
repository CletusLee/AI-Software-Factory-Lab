"""Run the local PAY-482 demonstration and write an HTML execution report."""
import base64
import ast
import html
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
settings = {}
for line in (ROOT / '.env').read_text(encoding='utf-8-sig').splitlines():
    if '=' in line and not line.lstrip().startswith('#'):
        key, value = line.split('=', 1)
        settings[key.strip()] = value.strip().strip('"\'')

auth = base64.b64encode((settings['LANGFUSE_PUBLIC_KEY'] + ':' + settings['LANGFUSE_SECRET_KEY']).encode()).decode()
session_id = 'pay-482-demo-' + str(int(time.time()))
cases = [('stale', 'NOT READY'), ('passed', 'READY'), ('timeout', 'UNKNOWN')]
results = []

for scenario, expected in cases:
    boundary = 'agno-demo-boundary'
    fields = {'message': f'Check PAY-482 for Release Review. Use scenario {scenario}.', 'stream': 'false', 'session_id': session_id}
    body = ''.join(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n' for key, value in fields.items()) + f'--{boundary}--\r\n'
    request = urllib.request.Request('http://localhost:7777/agents/sdlc-ticket-agent/runs', data=body.encode(), headers={'Authorization': 'Bearer ' + settings['OS_SECURITY_KEY'], 'Content-Type': 'multipart/form-data; boundary=' + boundary})
    with urllib.request.urlopen(request, timeout=180) as response:
        run = json.load(response)
    tool_messages = [m for m in run.get('messages', []) if m.get('role') == 'tool' and m.get('tool_name') == 'check_ticket_readiness' and not m.get('from_history')]
    output = run.get('content') or ''
    tool_result = ast.literal_eval(tool_messages[-1]['content']) if tool_messages else {}
    passed = run.get('status') == 'COMPLETED' and tool_result.get('scenario') == scenario and tool_result.get('recommendation') == expected and expected in output
    if expected == 'READY' and 'NOT READY' in output:
        passed = False
    results.append({'scenario': scenario, 'expected': expected, 'passed': passed, 'run_id': run.get('run_id'), 'answer': output, 'tool': tool_messages[-1].get('content', '') if tool_messages else 'Missing tool call'})
    print(f"{scenario}: {'PASS' if passed else 'FAIL'} run={run.get('run_id')}", flush=True)

time.sleep(5)
request = urllib.request.Request('http://localhost:3001/api/public/traces?limit=100', headers={'Authorization': 'Basic ' + auth})
with urllib.request.urlopen(request, timeout=30) as response:
    traces = json.load(response).get('data', [])
session_traces = [t for t in traces if t.get('sessionId') == session_id]
for item in results:
    item['trace_id'] = None
    item['trace_verified'] = False
    for trace in session_traces:
        trace_request = urllib.request.Request('http://localhost:3001/api/public/traces/' + trace['id'], headers={'Authorization': 'Basic ' + auth})
        with urllib.request.urlopen(trace_request, timeout=30) as response:
            detail = json.load(response)
        observations = detail.get('observations', [])
        if any(o.get('metadata', {}).get('attributes', {}).get('agno.run.id') == item['run_id'] for o in observations):
            item['trace_id'] = trace['id']
            types = {o.get('type') for o in observations}
            item['trace_verified'] = {'AGENT', 'GENERATION', 'TOOL'}.issubset(types) and any(o.get('name') == 'check_ticket_readiness' for o in observations)
            break
    print(f"{item['scenario']} trace: {item['trace_id'] or 'not matched'}, verified={item['trace_verified']}", flush=True)

esc = lambda value: html.escape(str(value))
rows = ''.join(f"<tr><td>{esc(r['scenario'])}</td><td>{esc(r['expected'])}</td><td>{'PASS' if r['passed'] else 'FAIL'}</td><td><code>{esc(r['run_id'])}</code></td><td>{esc(r['trace_id'] or '未找到')}，{'Agent／模型／工具已驗證' if r['trace_verified'] else '追蹤未驗證'}</td></tr>" for r in results)
details = ''.join(f"<details><summary>{esc(r['scenario'])} — 工具結果與 Agent 回覆</summary><h3>工具結果</h3><pre>{esc(r['tool'])}</pre><h3>Agent 回覆</h3><pre>{esc(r['answer'])}</pre></details>" for r in results)
page = f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PAY-482 Agno → Langfuse Demo</title><style>body{{font:16px/1.65 system-ui,sans-serif;max-width:1100px;margin:40px auto;padding:0 24px;color:#1b293b}}h1,h2{{color:#173c60}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #cbd5e1;padding:9px;text-align:left;overflow-wrap:anywhere}}th{{background:#eaf2f8}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f2f5f8;padding:16px}}details{{padding:12px;border-bottom:1px solid #ddd}}.notice{{background:#fff3d8;padding:16px}}code{{overflow-wrap:anywhere}}</style></head><body><h1>PAY-482 工單送審示範</h1><p>本次執行時間 {esc(time.strftime('%Y-%m-%d %H:%M:%S'))}，session <code>{esc(session_id)}</code>。</p><p class="notice">PAY-482、SPEC、Oracle、CI 和審核者均為本機模擬資料。MiniMax 模型呼叫、AgentOS 與 Langfuse 為實際服務。此示範未執行付款系統測試、未連接 Azure Boards，也未完成真人驗收。</p><h2>情境與操作</h2><ol><li>啟動 docker compose 服務，確認 Agent UI 與 Langfuse 可以開啟。</li><li>於 Agent UI 選擇 SDLC Ticket &amp; Spec Assistant，輸入「檢查 PAY-482，情境 stale，是否可以送 Release Review？」</li><li>在同一對話依序輸入 passed 與 timeout，觀察 Agent 查詢本機工具的結果。</li><li>開啟 <a href="http://localhost:3001">Langfuse</a> 的 Traces，依時間、run ID 或 session 查閱 Agent、模型及工具呼叫。</li><li>QA / Owner 對照原始證據與 Oracle 進行獨立核對，正式驗收由授權人員決定。</li></ol><h2>本次實際執行結果</h2><table><thead><tr><th>情境</th><th>預期建議</th><th>檢查</th><th>Run ID</th><th>Trace ID</th></tr></thead><tbody>{rows}</tbody></table><p>檢查條件為 Agent 成功完成、呼叫工具，且工具結果和回覆包含預期建議。UNKNOWN 代表模擬 CI 資料無法取得。</p>{details}<h2>三層觀測</h2><p>L3 可檢查模型、工具、結果與錯誤。L2 須連接真實 Work／CI／QA 的開工與授權驗收事件。L1 的實際業務 Value 與營運品質需要真實部署及觀察，狀態為 Not Yet Measured。</p><h2>重新執行</h2><p>在專案目錄執行 <code>python demo_run.py</code>，會重新呼叫三次模型並覆寫本報告。模型使用量可能產生費用。Langfuse 頁面可按時間尋找追蹤。</p></body></html>'''
page = page.replace('此示範未執行付款系統測試、未連接 Azure Boards，也未完成真人驗收。', 'passed 情境實際執行本機記憶體帳本的兩項 unittest；commit 與 CI 證據為模擬。此示範未連接 Azure Boards，也未完成真人驗收。')
page = page.replace('<h2>三層觀測</h2>', '<h2>本機測試</h2><p>passed 情境在 AgentOS 容器內執行 <code>python -m unittest -v test_payment_demo</code>，涵蓋相同事件重送與不同事件正常入帳。Oracle 和程式為本機教學範例，測試輸出可展開上方工具結果查看。</p><h2>三層觀測</h2>')
output_dir = ROOT / 'swarm-output'
output_dir.mkdir(parents=True, exist_ok=True)
(output_dir / 'demo-report.html').write_text(page, encoding='utf-8')
if not all(r['passed'] and r['trace_verified'] for r in results):
    raise SystemExit('One or more scenarios or traces failed verification')

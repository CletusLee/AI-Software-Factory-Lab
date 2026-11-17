"""Render the latest AgentOS runs with their Tempo trace references."""
import html
import json
from datetime import datetime
from pathlib import Path
from string import Template

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / 'swarm-output'
GRAFANA_EXPLORE = 'http://localhost:3002/explore'
SCENARIOS = {
    'ready': '版本相符',
    'stale': '舊版證據',
    'timeout': 'CI 查詢逾時',
    'fail': '併發檢查失敗',
    'improvement': '改善分析',
}


def read_json(path, fallback):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return fallback


def esc(value):
    return html.escape(str(value))


def format_json(value):
    return html.escape(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def collect_steps(steps, depth=0):
    rows = []
    for step in steps or []:
        name = step.get('step_name') or step.get('name') or '未命名步驟'
        status = '成功' if step.get('success') else '失敗或未完成'
        rows.append((depth, name, status, step))
        children = step.get('step_results') or step.get('steps') or []
        rows.extend(collect_steps(children, depth + 1))
    return rows


def render_steps(steps):
    rows = collect_steps(steps)
    if not rows:
        return '<p class="muted">AgentOS 未回傳步驟明細。</p>'
    return ''.join(
        '<details class="step">'
        f'<summary style="--depth:{depth}"><span>{esc(name)}</span><b>{esc(status)}</b></summary>'
        f'<pre>{format_json({key: value for key, value in step.items() if key not in ("step_results", "steps")})}</pre>'
        '</details>'
        for depth, name, status, step in rows
    )


def render_run(item, improvement=False):
    scenario = 'improvement' if improvement else item.get('scenario', 'unknown')
    label = SCENARIOS.get(scenario, scenario)
    run = item.get('run', item)
    result = run.get('content') or {}
    trace_id = item.get('trace_id') or run.get('trace_id')
    trace_verified = item.get('trace_verified', run.get('trace_verified', False))
    business_ok = item.get('valid', run.get('status') == 'COMPLETED')
    business_status = '完成' if business_ok else '未完成'
    trace_status = '已驗證' if trace_verified else '未驗證'
    trace_link = (
        f'<a href="{GRAFANA_EXPLORE}" target="_blank" rel="noreferrer">在 Grafana Explore 開啟</a>'
        if trace_id else '<span class="muted">尚無 trace ID</span>'
    )
    trace_display = f'<code>{esc(trace_id)}</code>' if trace_id else ''
    names = item.get('trace_span_names') or run.get('trace_span_names') or []
    kinds = item.get('trace_span_kinds') or run.get('trace_span_kinds') or []
    span_details = (
        f'<p><b>Span 類型</b> {esc(", ".join(kinds) or "未回傳")}</p>'
        f'<p><b>Span 名稱</b> {esc(", ".join(names) or "未回傳")}</p>'
    )
    return (
        f'<article class="case"><h2>{esc(label)}</h2>'
        '<dl>'
        f'<dt>AgentOS 狀態</dt><dd>{esc(run.get("status", "UNKNOWN"))}</dd>'
        f'<dt>業務檢查</dt><dd>{esc(business_status)}</dd>'
        f'<dt>Run ID</dt><dd><code>{esc(run.get("run_id", "未知"))}</code></dd>'
        f'<dt>Trace</dt><dd>{esc(trace_status)} {trace_link}<br>{trace_display}</dd>'
        '</dl>'
        f'{span_details}'
        '<details><summary>AgentOS 執行結果</summary>'
        f'<pre>{format_json(result)}</pre></details>'
        f'<details><summary>Workflow 步驟（{len(collect_steps(run.get("step_results")))}）</summary>'
        f'{render_steps(run.get("step_results"))}</details>'
        '</article>'
    )


def main():
    data = read_json(OUTPUT / 'native-results.json', {})
    if not isinstance(data, dict):
        data = {}
    cases = data.get('cases', [])
    rendered = [render_run(item) for item in cases]
    if data.get('improvement'):
        rendered.append(render_run(data['improvement'], improvement=True))
    if not rendered:
        rendered.append('<article class="case"><p>尚無 Workflow 執行結果。請先執行 native_demo_run.py。</p></article>')
    completed = sum(bool(item.get('valid')) for item in cases)
    verified = sum(bool(item.get('trace_verified')) for item in cases)
    summary = f'Delivery 情境 {completed}/{len(cases)} 通過，Tempo trace {verified}/{len(cases)} 驗證完成。'
    template = Template((ROOT / 'native_report_template.html').read_text(encoding='utf-8'))
    report = template.substitute(
        generated_at=esc(datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')),
        summary=esc(summary),
        runs=''.join(rendered),
    )
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / 'native-report.html').write_text(report, encoding='utf-8')
    print('Generated swarm-output/native-report.html')


if __name__ == '__main__':
    main()

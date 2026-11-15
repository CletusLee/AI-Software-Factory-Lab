"""Render the PAY-482 workflow report from saved API runs and Langfuse spans."""
import html
import json
from base64 import b64encode
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from string import Template

from factory_swarm import ROLES

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / 'swarm-output'
REPORT_IMAGES = OUTPUT / 'report-images'
TAIPEI = timezone(timedelta(hours=8))
ROLE_TASKS = {name: task for _, name, _, task in ROLES}
AGENT_IDS = {'factory-' + number: name for number, name, _, _ in ROLES}
CASES = {
    'ready': ('版本相符', '候選與受測版本皆為 a1b2c3d，本機兩項測試通過。', '送交人工審查'),
    'stale': ('舊版證據', '候選為 a1b2c3d，模擬受測版本為 f0e1d2c。', '補跑當前候選版本'),
    'timeout': ('CI 查詢逾時', '模擬 CI 查詢未能取得當前版本的結果。', '補齊可回查的 CI 證據'),
    'fail': ('併發檢查失敗', '假設隔離環境中同一付款事件併發重送，產生兩筆入帳。', '修正後由操作者重新執行'),
    'improvement': ('改善分析', '以同一工單的風險、兩項本機測試通過、併發尚未驗證作為獨立分析輸入。', '根因與改善草案'),
}
TEAM_MEMBERS = {
    'Knowledge Team': ['Knowledge', 'Research', 'Memory', 'Context'],
    'Observability Team': ['Observability', 'Evaluation', 'Benchmark', 'Operations'],
    'Governance Team': ['Cost Control', 'Audit'],
}
GRAPH_TRACE_ID = 'f42d5cf2903deea7a1b013c5513df0ff'
GRAPH_CAPTURES = (
    ('langfuse-graph-entry.jpg', 296, 'Workflow 入口與 Knowledge Team',
     '從 FastAPI 入口走到交付 Workflow、Evidence Gate 和 Knowledge Team。'),
    ('langfuse-graph-parallel.jpg', 1230, 'Parallel Proposals 的三條提案支線',
     'Parallel Proposals 向下連到 Code、Infrastructure 和 Integration 三個提案步驟。'),
    ('langfuse-graph-review.jpg', 774, '委派工具與人工審查出口',
     '委派工具聚合了四次呼叫。Human Review Pending 後接 API 回應與結束節點。'),
)


def read_json(path, fallback=None):
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else fallback


def esc(value):
    return html.escape(str(value), quote=True)


def code(value):
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False, indent=2)
    else:
        try:
            parsed = json.loads(value)
            if isinstance(parsed, (dict, list)):
                value = json.dumps(parsed, ensure_ascii=False, indent=2)
        except ValueError:
            pass
    return f'<pre>{esc(value)}</pre>'


def flatten(steps):
    for step in steps:
        yield step
        yield from flatten(step.get('steps') or [])


def step_status(step):
    if not step:
        return '未執行', 'muted'
    if not step.get('success'):
        return '失敗', 'error'
    if step.get('stop'):
        return '停止', 'error'
    return '已執行', 'ok'


def runtime_name(name):
    return name.replace(' ', '_')


def delegation_table(team, trace):
    spans = trace.get('observations', [])
    leaders = {s['id'] for s in spans if s['name'] == f'{runtime_name(team)}.arun'}
    children = [s for s in spans if s['parent'] in leaders]
    rows = []
    for member in TEAM_MEMBERS[team]:
        calls = [s for s in children if AGENT_IDS.get(s.get('memberId')) == member]
        agents = [s for s in children if AGENT_IDS.get(s.get('agentId')) == member]
        statuses = '、'.join('失敗' if s['level'] == 'ERROR' else '完成' for s in agents)
        tasks = ''.join(f'<li>{esc(s["task"])}</li>' for s in calls if s.get('task'))
        rows.append(f'<tr><th scope="row">{esc(member)}</th>'
                    f'<td>{esc(statuses or "本次未觀測到")}</td>'
                    f'<td>{f"<ul>{tasks}</ul>" if tasks else "—"}</td></tr>')
    return ('<div class="table-scroll"><table><thead><tr><th>成員</th><th>Agent span</th>'
            '<th>Team 實際委派任務</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>')


def render_inspector(case_id, name, title, explanation, step, trace, executor=None):
    label, tone = step_status(step)
    data = ''
    if executor in ROLE_TASKS:
        data += f'<p><strong>角色任務</strong>　{esc(ROLE_TASKS[executor])}</p>'
        data += ('<p class="subtle">Agent 以提供的本機證據回覆，標明 UNKNOWN。'
                 '正式變更、批准及發布由授權流程處理。</p>')
    if executor in TEAM_MEMBERS:
        data += delegation_table(executor, trace)
    if executor:
        span = next((s for s in trace.get('observations', [])
                     if s['name'] == f'{runtime_name(executor)}.arun' and s.get('input')), None)
        if span:
            data += (
                f'<details><summary>展開實際輸入 · Langfuse</summary>{code(span["input"])}'
                f'<p>Span ID <code>{esc(span["id"])}</code></p></details>'
            )
    if step:
        if step.get('step_run_id'):
            data += f'<p class="subtle">步驟 Run ID <code>{esc(step["step_run_id"])}</code></p>'
        duration = (step.get('metrics') or {}).get('duration')
        if isinstance(duration, (int, float)):
            data += f'<p class="subtle">步驟耗時 {duration:.2f} 秒</p>'
        if step.get('error'):
            data += f'<p class="error">錯誤　{esc(step["error"])}</p>'
        data += f'<details><summary>展開實際輸出 · AgentOS</summary>{code(step.get("content"))}</details>'
    else:
        data += '<p class="subtle">此站在流程定義中可用，本次所選執行沒有對應的步驟紀錄。</p>'
    return (
        f'<article class="node-detail" id="detail-{case_id}-{name}" '
        f'data-node-detail="{name}"><h4>{esc(title)} <span class="pill {tone}">{label}</span></h4>'
        f'<p>{esc(explanation)}</p>{data}</article>'
    )


def render_case(case_id, run, trace):
    steps = {s.get('step_name'): s for s in flatten(run.get('step_results') or [])}
    inspectors = []

    def node(key, step_name, title, detail, executor=None):
        step = steps.get(step_name)
        status, tone = step_status(step)
        inspectors.append(render_inspector(case_id, key, title, detail, step, trace, executor))
        return (f'<a class="node {tone}" href="#detail-{case_id}-{key}" data-node="{key}">'
                f'<strong>{esc(title)}</strong><span>{esc(detail)}</span><small>{status}</small></a>')

    def team_branch(key, step_name, team, detail):
        header = node(key, step_name, team, detail, team)
        observations = trace.get('observations', [])
        leaders = {span['id'] for span in observations if span['name'] == f'{runtime_name(team)}.arun'}
        members = []
        for index, member in enumerate(TEAM_MEMBERS[team]):
            member_key = f'{key}-member-{index}'
            attempts = [s for s in observations
                        if s['parent'] in leaders and AGENT_IDS.get(s.get('agentId')) == member]
            errors = sum(s['level'] == 'ERROR' for s in attempts)
            tone = ('error' if errors else 'ok') if attempts else 'muted'
            label = (f'{len(attempts)} 次 · {errors} 次失敗' if errors else f'{len(attempts)} 次') if attempts else '本次未觀測到'
            members.append(f'<a class="member {tone}" href="#detail-{case_id}-{member_key}" '
                           f'data-node="{member_key}"><strong>{esc(member)}</strong><small>{label}</small></a>')
            contents = ''.join(
                f'<details><summary>第 {i} 次執行輸入 · {esc(span["level"])}</summary>'
                f'{code(span.get("input", "未留存輸入"))}<p>Span <code>{esc(span["id"])}</code></p></details>'
                f'<details><summary>第 {i} 次執行輸出</summary>{code(span.get("output", "未留存輸出"))}</details>'
                for i, span in enumerate(reversed(attempts), 1)
            )
            inspectors.append(
                f'<article class="node-detail" id="detail-{case_id}-{member_key}" data-node-detail="{member_key}">'
                f'<h4>{esc(member)} <span class="pill {tone}">{label}</span></h4>'
                f'<p><strong>角色任務</strong>　{esc(ROLE_TASKS[member])}</p>'
                f'<p>上游是 {esc(team)} 的委派。成員回覆由 Team 彙整。</p>{contents}</article>'
            )
        return (f'<div class="team-block">{header}<div class="delegation">↓ Team 委派　↑ 成員回覆</div>'
                f'<div class="members">{"".join(members)}</div></div>')

    arrow = '<div class="down" aria-hidden="true">↓</div>'
    if case_id == 'improvement':
        sequence = [
            team_branch('observe', 'Observability', 'Observability Team', '依案例風險和證據提出診斷。'),
            node('observe-check', 'Observability Check', '觀測狀態檢查', '目前版本在觀測 Team 失敗時停止。'),
            team_branch('govern', 'Governance', 'Governance Team', '從上一步結果整理成本與稽核建議。'),
            node('govern-check', 'Governance Check', '治理狀態檢查', '目前版本在治理 Team 失敗時停止。'),
            node('improve', 'Improvement', 'Improvement', '提出根因假設與驗證方向。', 'Improvement'),
            node('optimize', 'Optimization', 'Optimization', '將改善建議整理為版本化草案。', 'Optimization'),
        ]
        graph = arrow.join(sequence)
        notice = ('這筆歷史執行的 Observability Team 回傳 Request timed out。'
                  '當時仍續跑治理與改善，後續輸出以逾時訊息為前提。'
                  '目前版本已加停止檢查，這筆紀錄早於修正。')
    else:
        gate = node('gate', 'Evidence Gate', 'Evidence Gate', '執行本機 unittest，判讀選定的模擬證據。')
        decision = node('condition', 'Readiness', 'Readiness', '只有 READY 進入專家規劃。')
        blocked = node('blocked', 'Needs Evidence or Rework', '補證或返工', '回傳 NOT READY 或 UNKNOWN，等待操作者補證或重跑。')
        knowledge = team_branch('knowledge', 'Knowledge', 'Knowledge Team', 'Team leader 委派並綜合成員回答。')
        plan = node('plan', 'Plan', 'Planner', '把知識摘要整理成工作與驗證計畫。', 'Planner')
        design = node('design', 'Design', 'Architect', '把計畫轉成交易邊界與唯一鍵設計。', 'Architect')
        expert_nodes = ''.join([
            node('code', 'Code Proposal', 'Coder', '修補候選與程式風險。', 'Coder'),
            node('infra', 'Infrastructure Proposal', 'Infrastructure', '隔離環境與回滾。', 'Infrastructure'),
            node('integration', 'Integration Proposal', 'Integration', 'Webhook 介接契約。', 'Integration'),
        ])
        review = node('review', 'Review', 'Reviewer', '收齊三份建議後指出審查缺口。', 'Reviewer')
        risk = node('risk', 'Risk Summary', 'Risk & Approval', '整理人工審查所需的確認事項。', 'Risk & Approval')
        pending = node('pending', 'Human Review Pending', '等待人工審查', '送審建議，released=false。')
        fan = ('<div class="fan"><div class="fan-label">1 → 3　同一份設計分送三站</div>'
               '<div class="fork" aria-hidden="true"><i></i><i></i><i></i></div>'
               f'<div class="parallel">{expert_nodes}</div>'
               '<div class="fork merge" aria-hidden="true"><i></i><i></i><i></i></div>'
               '<div class="fan-label">3 → 1　三份輸出匯入 Reviewer</div></div>')
        graph = (gate + arrow + decision +
                 '<div class="branches"><div class="branch"><span class="route">READY ↓</span>' +
                 arrow.join([knowledge, plan, design, fan, review, risk, pending]) +
                 '</div><div class="branch rejected"><span class="route">NOT READY / UNKNOWN ↓</span>' +
                 blocked + '</div></div>')
        notice = '選取任一節點查看這個案例實際交給 Agent 的輸入和這一站的輸出。'
    started = datetime.fromtimestamp(run['created_at'], TAIPEI).strftime('%Y-%m-%d %H:%M:%S') if run.get('created_at') else '—'
    duration = (run.get('metrics') or {}).get('duration')
    time_label = f'{duration:.2f} 秒' if isinstance(duration, (int, float)) else '—'
    title, scenario, next_action = CASES[case_id]
    content = run.get('content')
    result = content.get('result', '—') if isinstance(content, dict) else '觀測逾時，部分步驟失敗'
    agents = sum(s['type'] == 'AGENT' for s in trace.get('observations', []))
    branch = run.get('status', '—')
    if case_id == 'improvement':
        branch = '部分步驟失敗' if any(not s.get('success') or s.get('stop') for s in steps.values()) else '完成'
    return f'''
    <section class="run" data-run="{case_id}" id="run-{case_id}">
      <div class="run-summary">
        <div><p class="overline">{esc(run.get("workflow_name"))}</p><h3>{esc(title)}</h3>
        <p>{esc(scenario)}</p><p><strong>結果</strong>　<code>{esc(result)}</code> · {esc(branch)}</p>
        <p><strong>後續</strong>　{esc(next_action)}</p></div>
        <dl><dt>執行輸入</dt><dd><code>{esc(run.get("input"))}</code></dd>
          <dt>實際執行</dt><dd>{started}（台北）· {time_label} · {agents} 個 Agent / Team spans</dd>
          <dt>Run ID</dt><dd><code>{esc(run.get("run_id"))}</code></dd>
          <dt>Trace ID</dt><dd><code>{esc(trace.get("id", "—"))}</code></dd>
        </dl>
      </div>
      <p class="notice">{esc(notice)}</p>
      <div class="workspace"><div class="graph" aria-label="{esc(title)}的流程圖">{graph}</div>
       <aside class="inspector" aria-label="節點執行證據"><p class="overline">節點紀錄</p>{''.join(inspectors)}</aside>
      </div>
      <details><summary>展開 Workflow 最終回傳值</summary>{code(content)}</details>
    </section>
    '''


def relationship_evidence(trace, run):
    spans = trace.get('observations', [])
    by_id = {s['agentId']: s for s in spans if s.get('agentId')}
    steps = {s.get('step_name'): s for s in flatten(run.get('step_results') or [])}
    architect = steps.get('Design', {}).get('content')
    reviewer = by_id.get('factory-10', {}).get('input') or ''
    specialists = [by_id.get(key, {}).get('input') for key in ('factory-04', 'factory-06', 'factory-08')]
    if not architect or not reviewer or not all(specialists):
        return ''
    shared = architect == specialists[0] == specialists[1] == specialists[2]
    combined = all(f'=== {name} ===' in reviewer for name in
                   ('Code Proposal', 'Infrastructure Proposal', 'Integration Proposal'))
    if shared and combined:
        return ('<p class="verify">已核對 ready 的 Langfuse 內容：三個專家的輸入完全相同，'
                'Reviewer 的輸入包含 Code Proposal、Infrastructure Proposal、Integration Proposal 三段。'
                '在流程圖點開任一節點可讀原文。</p>')
    return ''


def zoom_controls():
    return ('<div class="zoom-controls" hidden>'
            '<button type="button" data-zoom="-25" aria-label="縮小">−</button>'
            '<button type="button" data-zoom="reset" aria-label="重設為原尺寸">重設</button>'
            '<button type="button" data-zoom="25" aria-label="放大">+</button>'
            '<output aria-live="polite">100%</output></div>')


def trace_graph(trace):
    spans = trace.get('observations', [])
    if not spans:
        return ''
    by_id = {span['id']: span for span in spans}
    children = defaultdict(list)
    for span in sorted(spans, key=lambda span: span.get('start') or ''):
        parent = span.get('parent')
        children[parent if parent in by_id else None].append(span)

    def render_branch(parent):
        items = []
        for span in children[parent]:
            span_id = esc(span['id'])
            kind = esc(span['type'])
            member = AGENT_IDS.get(span.get('memberId'))
            target = f' → {esc(member)}' if member else ''
            items.append(
                f'<li id="observation-{span_id}"><details class="trace-observation"><summary class="trace-node">'
                f'<span class="trace-type" data-type="{kind}">{kind}</span>'
                f'<span>{esc(span["name"])}{target}</span></summary>'
                f'<p class="span-ids">Span ID <code>{span_id}</code> · Parent ID '
                f'<code>{esc(span.get("parent") or "—")}</code></p></details>'
                f'{render_branch(span["id"])}</li>'
            )
        return f'<ul>{"".join(items)}</ul>' if items else ''

    jumps = ('Knowledge', 'Plan', 'Design', 'Parallel_Proposals', 'Review',
             'Risk_Summary', 'Human_Review_Pending')
    step_ids = {span['name']: span['id'] for span in spans if span['type'] == 'CHAIN'}
    shortcuts = ''.join(
        f'<a href="#observation-{esc(step_ids[f"{name}.aexecute"])}">{name.replace("_", " ")}</a>'
        for name in jumps if f'{name}.aexecute' in step_ids
    )
    return (
        '<div class="capture-note zoomable trace-graph">'
        f'<h3 id="trace-graph-title">完整 Trace 呼叫圖 · {len(spans)} 個觀測節點</h3>'
        '<p>連線依實際父子呼叫繪製。可展開各節點查看 Span ID 與 Parent ID。'
        'Knowledge Team 下方可找到四次委派及各成員呼叫，Parallel Proposals 下方可找到三條提案。</p>'
        f'<nav class="trace-jumps" aria-label="跳到指定 Workflow 步驟">{shortcuts}</nav>'
        f'{zoom_controls()}'
        '<div class="graph-viewport" role="region" tabindex="0" aria-labelledby="trace-graph-title">'
        f'<div class="trace-tree">{render_branch(None)}</div></div></div>'
    )


def screenshot_figure(filename, width, title, caption, heading='h4'):
    path = REPORT_IMAGES / filename
    if not path.is_file():
        return ''
    screenshot = b64encode(path.read_bytes()).decode('ascii')
    figure_id = path.stem
    return (
        f'<figure class="langfuse-capture zoomable"><{heading} id="{figure_id}">{esc(title)}</{heading}>'
        f'{zoom_controls()}<div class="graph-viewport capture-viewport" role="region" tabindex="0" '
        f'aria-labelledby="{figure_id}"><img style="--capture-width:{width}px" '
        f'loading="lazy" src="data:image/jpeg;base64,{screenshot}" '
        f'alt="{esc(title)}"></div><figcaption>{esc(caption)}</figcaption></figure>'
    )


def graph_screenshots(trace):
    if trace.get('id') != GRAPH_TRACE_ID:
        return ''
    figures = '<div class="graph-captures">' + ''.join(
        screenshot_figure(*capture) for capture in GRAPH_CAPTURES
    ) + '</div>'
    overview = REPORT_IMAGES / 'langfuse-graph.jpg'
    if overview.exists():
        image = b64encode(overview.read_bytes()).decode('ascii')
        figures += (
            '<details class="capture-note langfuse-capture"><summary>原生 Graph 整體輪廓</summary>'
            f'<img loading="lazy" src="data:image/jpeg;base64,{image}" alt="Langfuse Aggregated Graph 全貌">'
            '</details>'
        )
    return figures


def screenshots(ready):
    agent_ui = screenshot_figure(
        'native-agent-ui.jpg', 254, 'Agent UI 的 Team 選單',
        '選單列出 Knowledge Team、Observability Team 和 Governance Team。',
        heading='h3',
    )
    captures = [
        ('langfuse-workflow.jpg', 1290, 'Trace Tree 與 Workflow 輸入／輸出',
         '右側選取 PAY_482_Delivery.arun。輸入是 PAY-482 scenario ready，輸出停在 READY_FOR_HUMAN_REVIEW，released 為 false。'
         '左側可看見 Knowledge Team 的四筆委派。'),
        ('langfuse-timeline.jpg', 1290, 'Langfuse 原生 Timeline',
         '左側依時間排列 Workflow、Team、委派工具和模型的 Span，右側顯示 Workflow 結果。'),
    ]
    figures = ''.join(screenshot_figure(*capture, heading='h3') for capture in captures
                      if ready.get('id') == GRAPH_TRACE_ID)
    langfuse = f'<div class="capture-note"><h3>平行步驟耗時</h3>{trace_timing(ready)}</div>'
    return figures + f'<div class="media">{langfuse}{agent_ui}</div>'


def trace_timing(trace):
    labels = {'factory-04': 'Coder', 'factory-06': 'Infrastructure', 'factory-08': 'Integration',
              'factory-10': 'Reviewer'}
    spans = {s.get('agentId'): s for s in trace.get('observations', [])
             if s.get('agentId') in labels and s.get('start') and s.get('end')}
    if len(spans) != len(labels):
        return ''
    times = {key: (datetime.fromisoformat(span['start']), datetime.fromisoformat(span['end']))
             for key, span in spans.items()}
    start = min(pair[0] for pair in times.values())
    end = max(pair[1] for pair in times.values())
    total = (end - start).total_seconds()
    if total <= 0:
        return ''
    rows = []
    for key, label in labels.items():
        begin, finish = times[key]
        offset = (begin - start).total_seconds()
        duration = (finish - begin).total_seconds()
        rows.append(f'<div class="timing-row"><b>{label}</b><div class="track">'
                    f'<span style="left:{offset / total:.2%};width:{duration / total:.2%}"></span></div>'
                    f'<small>+{offset:.2f}s · {duration:.2f}s</small></div>')
    return ('<h4>由實際 Span 時間繪製</h4><p class="subtle">以第一個平行 Agent 開始為 0 秒。'
            '三條支線重疊，Reviewer 在它們結束後才開始。</p>' + ''.join(rows))


def trace_comparison(runs, traces):
    rows = []
    for key in CASES:
        run, trace = runs.get(key, {}), traces.get(key, {})
        if not trace or trace.get('sessionId') != run.get('session_id'):
            continue
        spans = trace.get('observations', [])
        counts = Counter(s['type'] for s in spans)
        tokens = sum(int(s.get('tokens') or 0) for s in spans if s['type'] == 'GENERATION')
        errors = sum(s.get('level') == 'ERROR' for s in spans)
        rows.append(
            f'<tr><th scope="row">{esc(CASES[key][0])}</th>'
            f'<td>{len(spans)}</td><td>{counts["AGENT"]}</td><td>{counts["TOOL"]}</td>'
            f'<td>{counts["GENERATION"]}</td><td>{tokens:,}</td><td>{errors}</td></tr>'
        )
    if not rows:
        return ''
    return (
        '<div class="table-scroll"><table aria-label="Langfuse 追蹤摘要"><thead><tr>'
        '<th>情境</th><th>Observations</th><th>Agent / Team</th><th>工具</th>'
        '<th>模型呼叫</th><th>Tokens</th><th>錯誤層級</th></tr></thead><tbody>'
        + ''.join(rows) + '</tbody></table></div>'
        '<p class="subtle">Observations 包含 Workflow、Agent、工具、模型與 HTTP 等紀錄。'
        'Tokens 加總有提供用量的模型紀錄，錯誤欄計算標示 ERROR 的觀測項目。</p>'
    )


def main():
    data = read_json(OUTPUT / 'native-results.json')
    traces = read_json(OUTPUT / 'native-traces.json', {})
    runs = {case['scenario']: case['run'] for case in data['cases']}
    if data.get('improvement'):
        runs['improvement'] = data['improvement']
    labels = ''.join(f'<a href="#run-{key}" data-view="{key}">{esc(CASES[key][0])} <small>{key}</small></a>'
                     for key in CASES if key in runs)
    cases = ''.join(
        render_case(key, runs[key], traces.get(key, {}) if traces.get(key, {}).get('sessionId') ==
                    runs[key].get('session_id') else {})
        for key in CASES if key in runs
    )
    ready = traces.get('ready', {})
    if ready.get('sessionId') != runs.get('ready', {}).get('session_id'):
        ready = {}
    template = Template((ROOT / 'native_report_template.html').read_text(encoding='utf-8'))
    report = template.substitute(tabs=labels, runs=cases, media=screenshots(ready),
                                 graph_captures=graph_screenshots(ready), trace_graph=trace_graph(ready),
                                 comparison=trace_comparison(runs, traces),
                                 evidence=relationship_evidence(ready, runs.get('ready', {})))
    (OUTPUT / 'native-report.html').write_text(report, encoding='utf-8')
    print('Generated swarm-output/native-report.html')


if __name__ == '__main__':
    main()

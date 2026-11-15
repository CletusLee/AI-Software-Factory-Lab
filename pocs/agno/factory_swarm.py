"""Run the PAY-482 multi-agent demonstration with local evidence and Langfuse traces."""
import argparse
import html
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from string import Template

OUTPUT = Path(__file__).resolve().parent / 'swarm-output'
HANDOFF_COUNT = 3
HANDOFF_LIMIT = 600
SHARED_INSTRUCTION = (
    '只根據提供的本機示範證據與前序輸出作答。以繁體中文簡短說明產出與 UNKNOWN。'
    '不得聲稱已執行未提供的操作、已核准或已發布。'
)
ROLES = [
    ('25', 'Knowledge', '知識', '整理供應商事件重送規則與證據來源。'),
    ('12', 'Research', '知識', '確認事故影響、需求與仍需 Domain Owner 確認的未知項。'),
    ('02', 'Planner', '主線', '拆分 PAY-482 的實作與驗證工作，列出依賴。'),
    ('01', 'Orchestrator', '主線', '根據既有證據安排交接與測試失敗後的回流。'),
    ('15', 'Memory', '知識', '整理歷史 ADR 中帳務資料不可抹除的限制。'),
    ('03', 'Architect', '主線', '提出交易原子性、唯一鍵與資料一致性設計。'),
    ('14', 'Context', '知識', '整理帳務與 webhook 介面的必要脈絡。'),
    ('04', 'Coder', '主線', '根據測試證據提出修補候選及程式風險。'),
    ('06', 'Infrastructure', '主線', '提出隔離測試環境與回滾設定。'),
    ('08', 'Integration', '主線', '檢查 webhook 事件識別與回應契約。'),
    ('09', 'Testing', '驗證', '分析實際本機 unittest 結果與未覆蓋的測試。'),
    ('11', 'Security', '驗證', '提出簽章、跨商戶與權限驗證缺口。'),
    ('20', 'Reliability', '驗證', '解讀受控失敗案例，提出併發與重送風暴驗證。'),
    ('10', 'Reviewer', '驗證', '審查候選修正與測試證據，指出放行前尚缺事項。'),
    ('24', 'Risk & Approval', '治理', '整理人工審查清單及待確認事項，不替人核准。'),
    ('22', 'Release', '主線', '依證據草擬發布和回滾計畫，不實際發布。'),
    ('13', 'Documentation', '主線', '草擬 Wiki 更新，記下案例與證據來源。'),
    ('21', 'Observability', '觀測', '說明如何從 Trace、測試及工單資料診斷。'),
    ('16', 'Evaluation', '觀測', '設計 READY、NOT READY、UNKNOWN 的評估和預期結果。'),
    ('27', 'Cost Control', '觀測', '提出本次模型用量與配額紀錄方式，不假稱已設定閘道。'),
    ('17', 'Benchmark', '觀測', '設計同一組案例的改善前後比較與分母。'),
    ('30', 'Audit', '觀測', '檢查授權與證據缺口，不推定模擬核准為真人核准。'),
    ('23', 'Operations', '觀測', '根據模擬的重送延遲訊號提出唯讀定位步驟。'),
    ('26', 'Improvement', '治理', '提出併發重送問題的根因假設與驗證方案。'),
    ('19', 'Optimization', '觀測', '提出版本化 Skill 改善草案與重新評估方式。'),
]


def agent_instructions(name):
    return [f'你是 {name} 專業 Agent。', SHARED_INSTRUCTION]


def handoff_from(results):
    return [
        {'agent': r['name'], 'output': r['output'][:HANDOFF_LIMIT], 'status': r['status']}
        for r in results[-HANDOFF_COUNT:]
    ]


def agent_prompt(task, evidence, handoff):
    return (
        f'角色任務：{task}\n'
        f'本機證據：{json.dumps(evidence, ensure_ascii=False)}\n'
        f'最近交接：{json.dumps(handoff, ensure_ascii=False)}\n'
        '請給出具體產出與缺口，最多 180 字。'
    )


def main():
    import app  # Configures the existing OpenInference exporter.
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat
    from opentelemetry import trace

    OUTPUT.mkdir(exist_ok=True)
    session = 'pay482-swarm-' + uuid.uuid4().hex[:12]
    start = time.time()
    test = subprocess.run([sys.executable, '-m', 'unittest', '-v', 'test_payment_demo'], capture_output=True, text=True, timeout=30)
    # This controlled assertion represents the first failed review; it does not alter source files.
    try:
        assert len(['event-1', 'event-1']) == 1, '併發重送導致兩筆入帳（受控示例）'
    except AssertionError as exc:
        failure = str(exc)
    evidence = {
        'work_id': 'PAY-482',
        'source': '本機示範資料。工單、ADR、版本、部署、告警與人工核准均為模擬。',
        'incident': '相同 webhook event 重送可能導致重複入帳。',
        'spec': '同一事件應僅入帳一次，不同事件各自入帳。',
        'candidate': '本地記憶體帳本範例，並非交易資料庫實作。',
        'controlled_failure': failure,
        'local_unittest_status': 'PASS' if test.returncode == 0 else 'FAIL',
        'local_unittest_output': (test.stdout + test.stderr)[-1800:],
        'limitations': '沒有真實併發測試、簽章驗證、Azure Boards、CI 或人工核准；正式驗收 UNKNOWN。',
    }
    results = []
    tracer = trace.get_tracer('factory-swarm-demo')
    with tracer.start_as_current_span('PAY-482 multi-agent demo', attributes={'session.id': session, 'langfuse.session.id': session, 'work.id': 'PAY-482'}) as root:
        trace_id = format(root.get_span_context().trace_id, '032x')
        for number, name, group, task in ROLES:
            instructions = agent_instructions(name)
            agent = Agent(name=name, id='demo-' + number, model=OpenAIChat(id=os.getenv('MODEL_ID'), api_key=os.getenv('OPENAI_API_KEY'), base_url=os.getenv('OPENAI_BASE_URL'), reasoning_effort='low', timeout=45, max_retries=0), instructions=instructions, markdown=True)
            prompt = agent_prompt(task, evidence, handoff_from(results))
            begin = time.time()
            try:
                response = agent.run(prompt, session_id=session)
                output = str(response.content or '')
                status = 'COMPLETED' if output else 'EMPTY'
                tokens = getattr(response.metrics, 'total_tokens', None) if response.metrics else None
            except Exception as exc:
                output = f'{type(exc).__name__}: {exc}'
                status = 'ERROR'
                tokens = None
            record = {
                'number': number, 'name': name, 'group': group, 'task': task,
                'instructions': instructions, 'prompt': prompt,
                'status': status, 'output': output,
                'elapsed_seconds': round(time.time() - begin, 2), 'tokens': tokens,
            }
            results.append(record)
            print(f'{number} {name}: {status} ({record["elapsed_seconds"]}s)', flush=True)
    payload = {'session': session, 'trace_id': trace_id, 'test': evidence, 'results': results, 'duration_seconds': round(time.time() - start, 2)}
    (OUTPUT / 'swarm-results.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    write_report(payload)
    if test.returncode or any(r['status'] != 'COMPLETED' for r in results):
        raise SystemExit('Some demo steps failed; see the report.')


STAGES = (
    (2, '知識與需求', 'scenario'),
    (4, '規劃與設計', 'design'),
    (4, '實作建議', 'build'),
    (4, '測試與審查', 'verify'),
    (3, '風險、發布與文件', 'release'),
    (6, '觀測與營運', 'observe'),
    (2, '根因與改善', 'improve'),
)


def output_excerpt(output):
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    prose = next((line for line in lines if not line.startswith('#')), '')
    excerpt = prose.removeprefix('- ').replace('**', '').replace('`', '')
    return excerpt[:120] + ('…' if len(excerpt) > 120 else '')


def relationship_node(index, result):
    return (
        f'<button class="relation-node" type="button" data-related="{index}">'
        f'{index + 1:02} {html.escape(result["name"])}</button>'
    )


def write_report(data):
    e = html.escape
    evidence = data['test']
    results = data['results']
    nodes = []
    panels = []

    for index, result in enumerate(results):
        number, name = result['number'], result['name']
        handoff = handoff_from(results[:index])
        sources = results[max(0, index - HANDOFF_COUNT):index]
        source_labels = ''.join(
            f'<span class="source-chip">{e(r["number"])} {e(r["name"])}</span>' for r in sources
        ) or '<span class="source-chip">流程起點</span>'
        nodes.append(f"""
        <li class="agent-step" data-step="{index}">
          <button class="agent-node" type="button" data-index="{index}" aria-controls="detail-{e(number)}" aria-pressed="false">
            <span class="node-title"><span class="step-index">{index + 1:02}</span><strong>{e(name)}</strong><span class="agent-id">ID {e(number)} · {e(result['group'])}</span></span>
            <span class="node-task">{e(result['task'])}</span>
            <span class="node-handoff"><b>收到</b> {source_labels}</span>
            <span class="node-result"><b>輸出節錄</b> {e(output_excerpt(result['output']))}</span>
            <span class="node-status">{e(result['status'])} · {result['elapsed_seconds']} 秒</span>
          </button>
        </li>""")

        instructions = result.get('instructions', agent_instructions(name))
        prompt = result.get('prompt', agent_prompt(result['task'], evidence, handoff))
        prompt_origin = '執行時保存的 Prompt' if 'prompt' in result else '依本次執行的程式與留存資料重建'
        handoff_panels = ''.join(
            f'<details class="handoff-detail"><summary>{e(source["number"])} {e(item["agent"])} · {e(item["status"])}</summary><pre>{e(item["output"])}</pre></details>'
            for source, item in zip(sources, handoff)
        ) or '<p class="muted">第一站直接使用共用的 PAY-482 證據。</p>'
        successors = results[index + 1:index + HANDOFF_COUNT + 1]
        incoming = ''.join(
            relationship_node(i, results[i]) for i in range(max(0, index - HANDOFF_COUNT), index)
        ) or '<span>PAY-482 共用證據</span>'
        outgoing = ''.join(
            relationship_node(i, successor) for i, successor in enumerate(successors, index + 1)
        ) or '<span>本次流程終點</span>'
        tokens = f' · {result["tokens"]:,} tokens' if result.get('tokens') is not None else ''
        panels.append(f"""
        <article class="agent-panel" id="detail-{e(number)}" data-panel="{index}">
          <p class="eyebrow">第 {index + 1} 站 / {len(results)} · Agent ID {e(number)} · {e(result['group'])}</p>
          <h3>{e(name)}</h3>
          <p class="agent-task">{e(result['task'])}</p>
          <p class="execution">{e(result['status'])} · {result['elapsed_seconds']} 秒{tokens}</p>
          <div class="relations" aria-label="{e(name)} 的交接關係">
            <div><b>從這裡接收</b>{incoming}</div>
            <span aria-hidden="true">→</span>
            <strong>{e(name)}</strong>
            <span aria-hidden="true">→</span>
            <div><b>輸出傳給</b>{outgoing}</div>
          </div>
          <h4>角色指令</h4><pre>{e(chr(10).join(instructions))}</pre>
          <h4>Demo 輸入與交接</h4>
          <p>共用證據包含工單、規格、受控失敗案例與本機測試結果。以下是此站收到的前序輸出，每筆最多 600 字。</p>
          {handoff_panels}
          <details class="prompt-detail"><summary>展開完整使用者 Prompt</summary><p class="muted">{prompt_origin}</p><pre>{e(prompt)}</pre></details>
          <h4>實際模型輸出</h4><pre class="model-output">{e(result['output'])}</pre>
        </article>""")

    stage_html = []
    overview = []
    start = 0
    for count, title, key in STAGES:
        if start >= len(nodes):
            break
        end = min(start + count, len(nodes))
        overview_nodes = ''.join(
            f'<button type="button" class="map-node" data-jump="{index}"><span>{index + 1:02}</span> {e(results[index]["name"])}</button>'
            for index in range(start, end)
        )
        overview.append(f'<div class="map-stage {key}"><a href="#stage-{key}">{e(title)}</a>{overview_nodes}</div>')
        stage_html.append(f"""
        <section class="stage {key}" id="stage-{key}">
          <h3>{e(title)} <span>第 {start + 1}–{end} 站</span></h3>
          <ol class="agent-chain" start="{start + 1}">{''.join(nodes[start:end])}</ol>
        </section>""")
        start = end
    if start < len(nodes):
        stage_html.append(f'<section class="stage"><h3>後續執行</h3><ol class="agent-chain" start="{start + 1}">{"".join(nodes[start:])}</ol></section>')

    template = Template(Path(__file__).with_name('swarm_report_template.html').read_text(encoding='utf-8'))
    report = template.substitute(
        stages=''.join(stage_html), panels=''.join(panels), overview=''.join(overview),
        completed=sum(r['status'] == 'COMPLETED' for r in results), total=len(results),
        test_status=e(evidence['local_unittest_status']), duration=data['duration_seconds'],
        incident=e(evidence['incident']), spec=e(evidence['spec']), failure=e(evidence['controlled_failure']),
        unittest_output=e(evidence['local_unittest_output']),
        session=e(data['session']), trace_id=e(data['trace_id']),
    )
    OUTPUT.mkdir(exist_ok=True)
    (OUTPUT / 'swarm-report.html').write_text(report, encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report-only', action='store_true', help='Render the report from the saved run.')
    args = parser.parse_args()
    if args.report_only:
        write_report(json.loads((OUTPUT / 'swarm-results.json').read_text(encoding='utf-8')))
    else:
        main()

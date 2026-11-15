"""Legacy one-time migration; exits once shared Factory definitions exist."""
import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT.parents[1] / 'definitions'
if ((DEST / 'workflows' / 'software-delivery' / 'workflow.json').is_file()
        and (DEST / 'workflows' / 'continuous-improvement' / 'workflow.json').is_file()):
    print('Shared Factory definitions already exist; this legacy one-time migration will not overwrite them.')
    raise SystemExit(0)
module = ast.parse((ROOT / 'factory_swarm.py').read_text(encoding='utf-8'))
roles = next(ast.literal_eval(n.value) for n in module.body if isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id == 'ROLES' for t in n.targets))

# The output contract and evidence requirements are deliberately role-specific.
details = {
 'Knowledge': ('彙整付款事件重送、冪等與可用知識；標明文件版本及來源。', 'evidence-review,webhook-contract', '知識摘要、來源、衝突與待確認問題'),
 'Research': ('釐清事故影響、利害關係人與尚未證實的產品需求；列出後續查證問題。', 'evidence-review', '需求與影響、證據、假設、待 Domain Owner 確認事項'),
 'Planner': ('依依賴將設計、修補、測試、審查及回滾拆成可驗收工作；標示阻塞。', 'delivery-planning', '工作項目、前置依賴、驗收條件、未知與交接對象'),
 'Orchestrator': ('根據已提供的步驟結果建議下一個交接及失敗回流；不得假裝已執行調度。', 'delivery-planning,evidence-review', '狀態、下一步、負責角色、阻塞與回流條件'),
 'Memory': ('整理已提供的歷史決策與帳務不得抹除限制，不推測未提供的記憶。', 'adr-documentation,evidence-review', '既有決策、適用限制、來源與未知'),
 'Architect': ('設計事件唯一鍵、交易邊界及併發重送下的帳務一致性，列出取捨。', 'idempotency-transaction-design,adr-documentation', '設計、資料及交易邊界、失敗模式、待驗證假設'),
 'Context': ('整理 webhook、商戶、帳本及關聯介面所需的情境與資料契約。', 'webhook-contract,evidence-review', '上下文、資料流、契約、來源及未知'),
 'Coder': ('根據設計與測試證據提出修補方向或程式碼草案；明確指出尚未實際寫檔。', 'patch-proposal,idempotency-transaction-design', '候選修改、對應設計、驗證方式、風險及未執行事項'),
 'Infrastructure': ('提出隔離的測試環境、設定、部署順序與可回滾方案。', 'deployment-rollback', '環境依賴、設定建議、部署和回滾條件'),
 'Integration': ('檢查 webhook 事件識別、簽章、重試與回應契約，區分供應商未知規則。', 'webhook-contract,webhook-security', '契約檢查、資料流、重送語意、缺口'),
 'Testing': ('分析提供的測試結果並設計重送、競態及失敗復原測試，不杜撰測試執行。', 'payment-testing,evidence-review', '已執行結果、覆蓋缺口、測試案例及預期'),
 'Security': ('檢視簽章驗證、防重放、商戶隔離及授權風險；沒有證據時標示未知。', 'webhook-security', '威脅、現有證據、缺口與建議驗證'),
 'Reliability': ('分析競態、重試風暴、逾時及部分失敗；規劃可靠度驗證。', 'payment-testing,root-cause-analysis', '失敗模式、影響、復原與驗證方案'),
 'Reviewer': ('彙整平行提案，檢查交易一致性、相容性及測試證據；列出阻擋項。', 'evidence-review,payment-testing', '審查結論、證據、衝突、阻擋與交接'),
 'Risk & Approval': ('彙整風險、例外和人工核准條件；不得把送審建議表述為核准。', 'audit,delivery-planning', '風險清單、缺證、待決事項與人工審查人'),
 'Release': ('根據可用證據草擬發布與回滾清單，缺少授權或證據時不得宣布發布。', 'deployment-rollback,audit', '發布前條件、觀測、回滾觸發及待核准'),
 'Documentation': ('將已提供的設計、測試和決策整理成可追溯文件草稿。', 'adr-documentation,evidence-review', '變更摘要、契約、證據引用、未知與後續'),
 'Observability': ('解讀提供的 trace、測試及工單，指出 span 與時間線的可證實關聯。', 'trace-diagnosis,evidence-review', '觀測摘要、trace 證據、異常及未知'),
 'Evaluation': ('設計 READY、NOT READY、UNKNOWN 案例和評分規則，區分期望與實際。', 'evaluation-benchmark', '測試集、預期、評估規則、實際資料與缺口'),
 'Cost Control': ('分析已提供的模型用量與價格；缺任何欄位則不估造成本。', 'model-usage-cost', '使用量、成本依據、限制、未知與建議'),
 'Benchmark': ('設計可重現的前後比較，固定資料集、分母、模型及評估方式。', 'evaluation-benchmark', '基線、實驗條件、指標、分母及資料缺口'),
 'Audit': ('檢查決策來源、執行證據和授權紀錄，不把模擬資料當真實核准。', 'audit,evidence-review', '可追溯紀錄、授權、缺口及待查事項'),
 'Operations': ('依提供的延遲與錯誤訊號提出唯讀排查和升級步驟。', 'trace-diagnosis,root-cause-analysis', '症狀、檢查、可能原因、證據及升級條件'),
 'Improvement': ('以觀測及治理結果提出根因假設、改善方案和可驗證的實驗。', 'root-cause-analysis,evaluation-benchmark', '根因假設、改善、驗證指標、風險及未證實事項'),
 'Optimization': ('提出版本化 Skill 或 prompt 改善草案、對照評估及回滾準則。', 'evaluation-benchmark,model-usage-cost', '變更草案、基線、驗收指標與回滾準則'),
}
skills = {
 'evidence-review': '確認來源、時間、版本與證據是否支持結論；缺證標 UNKNOWN。',
 'webhook-contract': '檢查事件識別、來源、順序、重試語意、回應與相容性。',
 'adr-documentation': '記錄背景、選項、決策、取捨、來源與未決問題。',
 'delivery-planning': '拆分依賴、驗收、負責角色、阻塞及人工交接。',
 'idempotency-transaction-design': '評估事件唯一鍵、交易邊界、併發和失敗恢復。',
 'patch-proposal': '連結問題、候選變更、影響、測試及回滾；草案不等於執行。',
 'payment-testing': '設計重複事件、競態、跨商戶、失敗與恢復測試。',
 'deployment-rollback': '定義發布前檢查、觀測、回滾觸發和資料保護。',
 'audit': '保留來源、版本、授權與決策；未見證據不得推定核准。',
 'trace-diagnosis': '根據實際 trace 和時間線定位症狀，區分觀察與假設。',
 'evaluation-benchmark': '定義資料集、基線、分母、預期、實際及通過標準。',
 'model-usage-cost': '記錄模型、token、價格與期間；缺失欄位標示 UNKNOWN。',
 'root-cause-analysis': '區分現象與假設，提出可反駁的驗證及後續行動。',
 'webhook-security': '檢視簽章、防重放、權限和商戶隔離。',
}

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding='utf-8')

def jwrite(path, obj):
    write(path, json.dumps(obj, ensure_ascii=False, indent=2) + '\n')

for key, text in skills.items():
    write(DEST / 'skills' / key / 'SKILL.md', f'---\nname: {key}\ndescription: {text}\n---\n\n# {key}\n\n{text}\n\n僅使用提供的資料；列出來源和未知，勿宣稱未執行的操作。\n')
for number, name, group, task in roles:
    responsibility, selected, output = details[name]
    aid = 'factory-' + number
    agent_dir = DEST / 'agents' / (aid + '-' + re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-'))
    jwrite(agent_dir / 'agent.json', {'id': aid, 'name': name, 'group': group,
           'summary': task, 'skills': selected.split(','), 'inputs': 'PAY-482 本機證據與前序輸出', 'outputs': output})
    write(agent_dir / 'prompt.md', f'# {name}\n\n## 角色與任務\n{responsibility}\n\n## 輸入\nPAY-482 情境、工具或前序步驟提供的證據和輸出。\n\n## 輸出格式\n{output}。每項結論附上可辨識的證據來源；無法確認時標示 UNKNOWN。\n\n## 限制\n僅依提供證據作答，區分事實、模擬資料和建議；不可宣稱已修改程式、執行測試、批准或發布。以繁體中文回覆。\n')

jwrite(DEST / 'agents/sdlc-ticket-agent/agent.json', {'id': 'sdlc-ticket-agent', 'name': 'SDLC Ticket & Spec Assistant', 'group': '入口', 'summary': '查詢 PAY-482 模擬工單及本機測試證據。', 'skills': ['evidence-review'], 'inputs': '工單及 stale、passed 或 timeout 情境', 'outputs': '工具結果、證據與人工審查建議'})
write(DEST / 'agents/sdlc-ticket-agent/prompt.md', '# SDLC Ticket & Spec Assistant\n\n每次回答必須呼叫 check_ticket_readiness，按使用者指定的 stale、passed 或 timeout 查詢；未指定使用 stale。忠實引用工具判定與證據，明確標示模擬資料；無法確認標 UNKNOWN。正式驗收與發布由授權人員決定。以繁體中文回答。\n')

teams = [ ('knowledge-team', 'Knowledge Team', ['factory-25','factory-12','factory-15','factory-14']), ('observability-team','Observability Team',['factory-21','factory-16','factory-17','factory-23']), ('governance-team','Governance Team',['factory-27','factory-30']) ]
for tid, name, members in teams:
    jwrite(DEST / 'teams' / tid / 'team.json', {'id': tid, 'name': name, 'members': members})
    write(DEST / 'teams' / tid / 'prompt.md', f'# {name}\n\n根據本機示範資料按需委派成員，彙整其回覆並附上證據來源與 UNKNOWN。標明委派取決於當次 Team 執行，不得代替人工核准。\n')

def step(name, typ, ref=None):
    v = {'name': name, 'type': typ}
    if ref: v['ref'] = ref
    return v

delivery = {'id':'pay-482-delivery', 'name':'PAY-482 Delivery', 'description':'證據判斷、平行專家建議與待人工審核。', 'steps':[
 step('Evidence Gate','executor','evidence_gate'),
 {'name':'Readiness','type':'condition','ref':'is_ready','steps':[
 step('Knowledge','team','knowledge-team'), step('Plan','agent','factory-02'), step('Design','agent','factory-03'),
 {'name':'Parallel Proposals','type':'parallel','steps':[step('Code Proposal','agent','factory-04'), step('Infrastructure Proposal','agent','factory-06'), step('Integration Proposal','agent','factory-08')]},
 step('Review','agent','factory-10'), step('Risk Summary','agent','factory-24'), step('Human Review Pending','executor','pending_approval')],
 'else_steps':[step('Needs Evidence or Rework','executor','blocked_result')]}]}
improvement = {'id':'pay-482-improvement','name':'PAY-482 Improvement','description':'以觀測與治理建議產生版本化改善草案。','steps':[
 step('Observability','team','observability-team'), step('Observability Check','executor','require_observability'),
 step('Governance','team','governance-team'),step('Governance Check','executor','require_governance'),
 step('Improvement','agent','factory-26'),step('Optimization','agent','factory-19')]}
for flow in (delivery, improvement):
    jwrite(DEST / 'workflows' / flow['id'] / 'workflow.json', flow)
print(f'Created definitions for {len(roles)+1} agents, {len(skills)} skills, {len(teams)} teams and 2 workflows')

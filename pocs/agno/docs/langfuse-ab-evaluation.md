# Agno Factory 的 agent、專案 skill 與 workflow A/B 評估

這份交接以 `pocs/agno` 的 Langfuse 版本為研究對象。研究問題是，Coder 或 Testing 取得專案專用 skill 之後，能否多找出真正的問題、少報錯誤，並改善最後的交付判斷？先用兩個專案的固定案例驗證。建議用離線成對重跑比較，第一輪只動一個角色。本文是實作計畫，尚無 A/B 實測結果。

Agno POC 已實作 per-work-item project skill context、PAY-482 與 INVENTORY-101 案例、Langfuse hosted dataset runner、A/B 評分和 Reviewer gate。尚未對執行中的 Langfuse/AgentOS 做接線 smoke 或實際跑 A/B，採用組合仍未決定。

## 現況與設計改動

| 現有行為 | 建議怎麼改 | 從哪裡接手 |
| --- | --- | --- |
| 25 個 factory agent 加上 Ticket agent 已能個別呼叫。角色 skill 在啟動時固定，Testing、Reviewer、Reliability 都長期綁定 `payment-testing`。 | 保留穩定的角色 ID 與主軸 skill。讓工作項目選填「角色 ID → 已登錄的專案 skill」，例如支付規則可同時供 Coder 和 Testing 使用。每次呼叫各自解析，避免兩張並行工單互用設定。Ticket agent 的獨立建構入口也要涵蓋。 | [agent 定義](../../../definitions/agents)、[agent 與 team 建立](../native_workflows.py)、[AgentOS 註冊](../app.py) |
| 現有 demo 傳入工單 ID 和情境。Evidence Gate 回傳判定與版本等證據，前段 Coder 卻要審查具體變更。 | 個別 agent、team 委派和 workflow 從同一 `work_id` 解析問題、驗收條件、允許檔案及相關程式片段或 diff。Testing 再取得該次執行的測試證據。工單沒有專案 skill 時使用角色預設。 | [工單範例](../../../scenarios/pay-482/work-item.json)、[Evidence Gate 與 executors](../native_workflows.py) |
| Ticket agent 在 `passed` 分支固定執行支付測試。第二個專案可能收到與其程式無關的測試結果。 | 用工單與候選版本找到對應的驗證紀錄，回傳命令、結果和來源。缺少相符紀錄時回傳 `UNKNOWN`。 | [Ticket 工具](../app.py) |
| 變更由 executor 套用工單內預寫的 patch。最後送審 gate 檢查步驟是否執行成功，未採計 Reviewer 在內容中提出的阻擋項。 | 保留隔離目錄及修改前失敗、修改後通過的測試。讓 Reviewer 回傳可讀取的決定和證據，遇到明確阻擋就進入補件，缺件或判讀失敗則為 `UNKNOWN`。另行評分 Coder 的分析。 | [交付流程](../../../definitions/workflows/software-delivery/workflow.json)、[送審 gate 與測試](../test_native_workflows.py) |

先在 Coder 和 Testing 實作上述共用入口，再讓其餘角色沿用。每個專案只寫可核對的程式規則。例如 PAY-482 遇到相同事件 ID、不同金額時應拒絕，並保留原帳目。Coder 要指出會出錯的分支。Testing 要能從實際測試分辨「驗了拋錯」和「也驗了原帳目」。[支付範例測試](../../../scenarios/pay-482/test_payment_demo.py)

## 第一個可重現的 A/B 實驗

**先測 Testing。** 讓 A、B 讀同一份驗收條件、diff 及測試證據，使用相同模型、角色 prompt 與工具。A 使用既有的 Testing skills。B 只替換其中 `payment-testing` 的內容，補上「拒絕衝突後，核對原帳目是否保留」這條規則。兩版共用相同的 skill 選擇機制。若另想測「依專案選 skill」本身的效果，就另開一輪，只切換綁定方式。角色 skill 和專案 skill 可以透過同一個穩定的 agent ID 比較。[Testing 定義](../../../definitions/agents/factory-09-testing/agent.json)、[現有 skill](../../../definitions/skills/payment-testing/SKILL.md)

實驗執行器在每次開始前選定 A 或 B，讓整次呼叫與 team 委派沿用同一組版本。最簡單可分開啟動兩組本機設定，各自讀固定的 definitions 快照。記下角色有哪些 skill 可用，若 trace 可見實際讀取事件再記讀了哪份。即使 B 沒有讀取新 skill，該次結果仍計入 B。

| 固定案例 | 評審事先寫好的預期 | 在哪一層計分 |
| --- | --- | --- |
| PAY-482，完整的衝突重送測試 | 辨認測試核對了 `ValueError` 和原帳目。沒有捏造缺口。 | Testing |
| 同一工單的對照測試，移除最後一個帳目斷言，其餘相同 | 即使所提供測試全綠，仍指出少驗了原帳目，並引用對應測試。 | Testing |
| 第二個非支付案例，例如定義 registry 引用不存在的 skill | Coder 能定位參照檢查。Testing 能核對未知 skill 的失敗測試。支付規則不應出現在結論中。 | Coder、Testing |
| 既有 `ready / stale / timeout / fail` 四個情境，再加一例「Reviewer 成功回覆但列出阻擋項」 | 前四例沿用 benchmark 預期。新增例應補件，所有案例均維持 `released=false`。 | Workflow |

前兩例可從同一測試產生兩份唯讀輸入。預期答案和評分規則只給評估器，以實際提供的那份原始碼為準。既有四個情境只有 `ready` 會經過 Coder 和 Testing。另外三個可衡量 Evidence Gate，不進角色品質的分母。第二個專案用來檢查技能是否誤用。兩個專案各留一筆未參與調整的案例供最後複核。[既有四個案例](../../../benchmark/pay-482-cases.json)、[交付步驟](../../../definitions/workflows/software-delivery/workflow.json)、[registry 檢查](../integration/registry.py)

## 評分與選版方式

| 對象 | 評什麼 | 如何判讀 |
| --- | --- | --- |
| Agent 的一次輸出 | `finding_correct`。事先寫下必要發現、可引用的檔案或測試，以及會造成誤判的說法。 | 必要發現正確且證據相符才通過。沒有缺口的對照案例若被判成有缺口也算錯。第一版逐 agent 呼叫 AgentOS，將分數記在該次 dataset item trace。Trace 內保留 Agno agent 與 model observations，從單一案例可複核完整執行。 |
| Workflow 的一次執行 | `outcome_correct` 核對預期狀態。`gate_violation` 記錄錯誤放行、越過人工核准或宣稱已發布。 | 用程式核對狀態、實際分支和 `released`，分數掛在整次 trace。正確停在 `UNKNOWN` 可以得分。另列模型逾時、執行錯誤、缺分與未經過的步驟。 |
| 通過品質門檻的組合 | 每案 tokens、端到端耗時，以及有可靠價格資料時的成本。 | 比較同案差值，缺資料保留空值。測試通過只能證明候選程式符合已執行的測試，無法替 Coder 的發現加分。 |

狀態與檔案參照先用程式驗。程式無法判讀的語意，讓一位不知道 A/B 身分的評審用固定規則判讀兩版與原始證據。只有量變大後才考慮用已校準的模型評審。對照頁可以逐案查看差異與分數，正式採用門檻要由團隊先決定。[Langfuse 分數模型](https://langfuse.com/docs/evaluation/scores/data-model) · [官方比較實驗指引](https://langfuse.com/docs/evaluation/experiments/compare-experiments)

1. **凍結比較條件。** 角色實驗先固定共用輸入與評分規則。比較完整 workflow 之前，再把必要的 gate 修正納入兩側基準。固定案例版本、驗收證據、模型與實際參數、工具、超時與重試策略。用新 session 和隔離工作目錄交錯執行 A/B、B/A。若調整評分標準，兩版輸出都須重評。
2. **先選 agent，再驗組合。** 用同一份已保存的上游輸入單獨測 Testing，再以相同方法測 Coder。進入完整流程時，先比較同一 workflow 的既有與候選 agent。接著固定 agent，比較一項 workflow 改動，例如 Reviewer 是否明確收到各平行分支的證據。若兩項改動可能互相影響，才比較四個組合（舊流程＋舊 agent、舊流程＋新 agent、新流程＋舊 agent、新流程＋新 agent）。
3. **只採用通過複核的組合。** 建議首輪每個有模型參與的案例、每版跑三次，交接報告列逐案勝／平／負與錯誤。這個次數用來看波動。正式決策以不同案例為單位，另看保留案例是否重現。事前可約定「關鍵案例零錯放，沒有新增的關鍵退步，目標案例有可重現的改善」。品質打平才比較成本和延遲。差異不穩或有缺分就保留基準版，補案例後再判。結果只適用於這批任務與已測組合。

日後若有足量真實工單，可再按工單隨機分派 A 或 B，讓同一工單從頭到尾維持同組，觀察人工接受率與退回補件率。現階段外部工單和核准屬模擬資料，先用離線案例選出值得試行的組合。[POC 範圍與限制](../README.md)

## Langfuse 接點

1. **沿用自架 Langfuse。** Compose 使用 Langfuse `:3` 映像。實作時先記錄實際執行的 server 版本與 image digest。官方相容表列出 v3 系列從 3.63.0 開始支援 Python SDK v4，可在實驗執行器固定一個相容的小版本。AgentOS 繼續用現有的 OTel exporter。自架 v4 才提供新版 Experiments 查詢 API。[POC Compose](../docker-compose.yml) · [自架版本相容表](https://langfuse.com/self-hosting/upgrade/versioning) · [Experiments API 適用版本](https://langfuse.com/docs/api-and-data-platform/features/public-api)
2. **把固定案例建成自架專案裡的一份 dataset。** 每筆 item 有穩定的案例 ID、給 agent 的 input，以及僅供評分的 expected output。用相容的 experiment runner 呼叫 AgentOS。A、B、各次重複各有自己的 dataset run 名稱，例如 `testing-A-r1` 和 `testing-B-r1`。同一 item 在單一 run 僅出現一次，才方便逐案配對。[官方離線實驗指南](https://langfuse.com/docs/evaluation/get-started/offline) · [實驗資料模型](https://langfuse.com/docs/evaluation/experiments/data-model)
3. **讓同一次案例執行共用一個 trace ID。** 實驗執行器在該 item 的活動 span 中發出 HTTP 請求，將 W3C `traceparent` 注入標頭。AgentOS 的 HTTP 入口還原該 context，讓既有的 workflow、agent、tool span 掛在同一棵樹上。把 Agno 回傳的 `run_id` 和活動 `trace_id` 一起存入該筆 benchmark 紀錄，分別對應工作流程結果與追蹤紀錄。重複實驗另起新 trace。[既有 Agno 追蹤設定](../app.py) · [OpenTelemetry 跨服務傳遞](https://opentelemetry.io/docs/languages/python/propagation/) · [Langfuse 分散式追蹤](https://langfuse.com/docs/observability/features/trace-ids-and-distributed-tracing)
4. **對準評分對象。** Workflow 結果以整次執行的 dataset item trace 評分。Agent 品質實驗會直接呼叫單一 agent，因此該 trace 評的是該 agent 的輸出，Agno `run_id` 和 Trace 內的 agent observation 可供複核。首版保留 trace 和 run 關聯，未另外查詢及寫入巢狀 observation ID。具體錯在哪個檔案、測試或判斷，記在 score comment。[Langfuse 評分層級](https://langfuse.com/docs/evaluation/scores/data-model)

**接線驗收可用 PAY-482 的 `ready` 案例。** 讓 A 與 B 各跑一次完整 workflow。在同一份 dataset 中應能找到兩個 run，每側的 item 都能打開各自的 trace。每棵 trace 都應能找到對應的 Agno run、Testing observation、workflow 分數及 Testing 分數。透過本機 benchmark 紀錄的 ID 再查一次。若只有 runner span，先檢查 HTTP 兩端的 context 傳遞，再開始批次跑實驗。

## 接手待辦與完成條件

依序完成前三項即可開始第一個角色實驗。建議第一個交付物是一張 Testing 的逐案比較表，附上每一筆的 trace 和評分理由。

- [x] **準備固定案例與評分規則。** 從 [benchmark](../../../benchmark/README.md) 延伸案例，保存固定輸入、預期發現、關鍵退步與保留集。PAY-482 開發案例與 INVENTORY-101 holdout 分開存放。評分答案獨立保存。
- [ ] **驗通 Langfuse 接線。** [實驗 runner](../native_experiment_run.py) 已在 HTTP 呼叫及 [AgentOS](../app.py) 入口傳遞 trace context。仍需用一筆案例確認 A/B 的各自 trace、workflow 與 agent 分數都出現在 Langfuse。
- [x] **固定版本，保留每次結果。** runner 透過 Langfuse dataset runs 保留每次變體結果和案例 ID，並記錄 Agno run ID、trace ID、定義版本、程式與案例內容雜湊、模型設定、評分規則及 Langfuse 版本。首版 agent 品質分數綁定該 agent 的 dataset item trace。
- [ ] **交付 Testing 第一張 A/B 表。** 先共用角色輸入與選 skill 的方式，再只替換一份 skill。每列包含「案例、A 的判斷與理由、B 的判斷與理由、預期、勝／平／負、兩側 trace」。對照無缺口案例與非支付案例，檢查新增誤報。同樣方式再驗 Coder。
- [x] **完成主流程的兩項修正。** Ticket 的 `passed` 查詢需提供候選 revision，並只採用相符候選目錄的實測結果。Reviewer 提出阻擋的案例回傳補件，缺少必要步驟或判讀失敗仍為 `UNKNOWN`。把這些行為納入後續 workflow 實驗的共同基準。[Ticket 工具](../app.py) · [現有 gate 測試](../test_native_workflows.py)
- [ ] **比較組合並留下決策。** 將入選角色接回交付流程，依前述順序比較。記錄採用或保留的版本、改善與退步的案例、保留集結果、成本或延遲差異，以及兩側 experiment run。讓持續改善 workflow 後續可引用這份決策，變更基準版仍由負責人確認。
- [ ] **推及其餘角色。** 驗證同一工單從單獨呼叫、team 委派或 workflow 進入時，角色都拿到該次應有的上下文。用兩張不同專案的並行工單檢查 skill 隔離。對每個確有專案規則的角色補一個可核對的案例即可。

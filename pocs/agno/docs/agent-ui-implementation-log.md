# Agno POC Agent UI 實作與驗證紀錄

本文件隨實作持續更新，供中斷後直接續接；最新 checkpoint 放在最上方。詳見[完整功能與驗收 checklist](agent-ui-capability-plan.md)與[UI 驗收及截圖證據](agent-ui-verification-evidence.md)。所有時間為台灣時間。只記錄本 POC 已觀察到的結果，不把其他 POC 的驗收結果移植成本 POC 證據。較早 checkpoint 的未勾選框代表當時尚未完成；目前待辦以本文件最上方「尚待資料、服務或裝置能力」及能力計畫中未完成主項／子項為準。

## 最新接手點（2026-11-22；production image `0a11f3…`）

- [x] **窄版 Workflow 與 Metrics fixture。** 375×844 的 ChatGPT 內建瀏覽器中，Workflow 線性 Graph 無水平溢位；Tree／Graph inspector 的初始焦點、Tab／Shift+Tab 循環、Escape／Close 焦點返回已驗。隔離 Metrics fixture 的缺失 `total_tokens` 顯示 Incomplete、不顯示部分總和；2 runs／0% success 顯示 100% failure。截圖在瀏覽器工具輸出，未存 repo；平行 Graph 欄數、真實失敗 run 及日期邊界仍待驗。
- [x] **Production 更新與清理。** Docker Compose build 通過（使用已通過編譯、lint、TypeScript 與 static generation 的快取層），只重建 `agent-ui`，目前 image `sha256:0a11f3d38a56df8924319a513a7c05f8395da99c123d901c3c28e55f3775465f`；首頁／health proxy 200，無授權 workflows 401。AgentOS 3.2.1 running、DB healthy；兩個 fixture containers 已停止。
- [x] **文件交接。** POC README 加入當前交付狀態；Agent UI repo README 更新功能、部署限制與 Token 行為，附上標明版本的歷史畫面。完整未完成項目以能力計畫為準。

## 前一 production checkpoint（2026-11-22；image `d2eb8f…`）

- [x] **Overview loading／error-state 保持資料庫選單。** `SourcePanel` 在 loading、error 且無 payload 時仍可選擇顯示固定 children；Recent sessions 永遠顯示 DB selector，config 尚在載入／401 時保留 URL 上的目前 DB，提示選項未載入，不保留舊 Token 的 DB list。ChatGPT browser final production reload 顯示 health/info 200、Factory/config/sessions 各自 401、無殘留 protected values，且 `AgentOS default` selector 仍可見。
- [x] **可重現的 Docker fixture setup 與 browser 驗收。** 新增 `mock-agentos-fixture.mjs` 及 `docker-compose.ui-fixture.yml`，Compose syntax validation 通過。隔離 mock 無 host port、fixture UI loopback-only 綁定 3002、bind-mount `agent-ui-delivery/src`；無真實 AgentOS token、DB mutation 或模型呼叫。ChatGPT in-app browser 驗成功空 sessions、403 no-permission／Retry、一次 HTTP 503 後 Retry 200、上游 socket drop 經 proxy 回 502 後 Retry 200。Slow DB A 切至 Fast DB B 後等待 A 延遲回應完成，UI 仍只顯示 B；loading／403 時 selector 和 Retry 都可見。
- [x] **F05 unknown step fixture 視覺驗收。** `/?view=workflows` 在 Tree 和 Graph 顯示 `Unsupported step (loop)`、`Unsupported step (router)`、`Unsupported step (custom_step)`。只驗 fallback labels，未知 step 執行語義和子分支仍未支援。Workflow Tree／Graph 與 Overview 403 截圖以 ChatGPT in-app browser screenshot API 擷取到工具輸出，未擷取整個電腦。
- [x] **Backstage Catalog Graph 修正。** `page:catalog-graph` 設 `rootEntityRefs: system:default/ai-factory`，Compose 將 app-config 唯讀掛載到 Backstage。Docker 重建 Backstage container 後 `/healthcheck`、`/catalog-graph` 為 200；ChatGPT in-app browser 顯示 Agents、Teams、Skills、Software Delivery、Continuous Improvement 節點和關係。唯讀 Catalog 有 48 entities（45 Components、Group、System、Location）、366 relations、0 unresolved targets。
- [x] **Agent／Team Workflow 引用矩陣唯讀覆核。** 從正在執行的 AgentOS 以 Bearer 授權 GET `/agents`、`/teams`、`/workflows` 及兩個 `/factory/workflows/{id}` definitions；只輸出 aggregate counts：2/2 definitions 成功、26 Agents 中 13 個被引用、3/3 Teams 被引用、0 個未解析的 Agent／Team refs。沒有輸出 Token、record IDs 或 definition body。UI 詳情頁的實際 browser 範例仍是 Testing Agent 與 Knowledge Team，其他頁面及 definition failure 隔離未逐一驗。
- [x] **唯讀分頁邊界抽樣。** 以 `limit=1` 對 Sessions、Memory、Learnings、Evals、Traces、Registry 查 page 1／2／999；全數 HTTP 200。Sessions 47 筆、Registry 69 筆（page 1／2 各 1 row、999 為 0）；Memory／Learnings／Evals／native Traces 各頁均 0 row／0 total pages。只輸出 status、回應 keys、row count 與 pagination metadata，未顯示或保存資料列。這是有限邊界樣本，不代表所有 GET 的 query／DB／page 組合。
- [x] **Final production build／deployment。** 完整 Docker build 通過 patch check/apply、Next compile、lint、TypeScript、static generation。第一次 deploy 後發現動態 `/api/agentos/[...path]` 未進入 patch、production 回 404；將新 route 加入 Git-generated patch，重建後 final image `sha256:d2eb8f10620c4e405bd360d1c14f436f3725b6f5e166c989abdb8c0df6d21b43` 已部署。Docker CLI：`/` 200、`/api/agentos/health` 200、無授權 `/api/agentos/workflows` 401；AgentOS 3.2.1 與 DB 未重建，DB healthy。
- [x] **Docker 收尾複核。** 停止本輪 `factory-agent-ui-fixture` 與 `factory-agentos-mock`；兩者現在為 exited，production `factory-agent-ui` 仍以 `sha256:d2eb8f…` running，AgentOS 3.2.1 running，Agno DB healthy。再次由 UI container 內查 `/`=200、`/api/agentos/health`=200、未授權 `/api/agentos/workflows`=401；未停止其他 Compose 服務。
- [x] **最終 browser 截圖紀錄。** ChatGPT browser screenshot API 擷取 final production Overview 401 狀態、fixture 403、Workflow Tree／Graph 與 Backstage Catalog Graph；畫面留在 browser tool output 並已目視核對，沒有 whole-computer screenshot。瀏覽器 API 仍沒有受支援的 repo 檔案輸出途徑，V05 file export 保持未完成。

## 前一 checkpoint 當時尚待資料、服務或裝置能力的項目（2026-11-22；已由上方最新狀態更新）

- 真實 AgentOS default 與具名 DB 都有近期 sessions；Overview 的成功空清單只以 mock fixture 驗證，不能作為實際部署資料證據。
- `/memories`、`/learnings` 是成功空集合；Knowledge config 回 404。尚無真實 Memory／Learning records 或已配置 Knowledge instance 可驗欄位、分頁與檢索來源。
- AgentOS native Traces／trace-session stats 為空。Langfuse 只有 0 datasets；2026-11-22 唯讀觀察 1 project／14,763 traces，10 筆 trace detail 抽樣未見 AgentOS run/session 關聯，故 F11/F13 的正向關聯與 A/B dataset run 仍未驗。沒有啟動新模型 run。
- FileSystem 四個 scoped GET 對 Testing Agent 回 404（未配置）；Media GET 回 503（storage 未配置），沒有 media key／內容。`/os/metrics/users` 因未設定 `user_directory` 回 503。
- F12 尚無真實 failed／0%-success run、缺欄位 Metrics response fixture 或日期邊界定義。F07 尚無 non-empty compaction record。
- Backstage Catalog Graph 空白問題已修正；目前整合缺口是 Langfuse trace↔AgentOS run mapping 與真實外部服務 outage fault injection。
- ChatGPT browser screenshots 已擷取並在工具輸出檢查，但無支援方法寫入 `docs/screenshots/`；實際 125% browser zoom 未驗。Workflow graph/node inspector 全鍵盤與完整頁面 Tab 稽核仍缺。
- P0.3 的 62/70 GET bounded sweep 已加上 Sessions、Memory、Learnings、Evals、Traces、Registry 的 page 1／2／999 樣本；仍未覆蓋 8 個 file/content/media routes、整個 GET surface 的 query／DB／page 組合及非空 Knowledge／Trace／Eval fixtures。P0.4 真實 AgentOS/model stream TCP abort 與 request-log UI／紀錄隔離仍未驗。P3 寫入／模型操作尚無明確 test target，未執行。

## 前一個 production checkpoint（2026-11-22；image `813fe12…`）

- [x] **F07 AgentOS 3.2.1 filter contract 與 UI 修正。** 對既有 Workflow session 執行唯讀比較：不帶 filter／`status=COMPLETED`／`status=ERROR` 分別回 200、200、200；`ERROR` 為成功空結果。`status=FAILED` 回 400，回應列出的有效值為 `CANCELLED`、`COMPLETED`、`ERROR`、`PAUSED`、`PENDING`、`REGENERATED`、`RUNNING`。`created_after`／`created_before` 以 ISO 字串送出會回 422；相同時間的 Unix epoch 秒回 200。UI 現在使用七種 status allowlist，本地攔截 `FAILED`，並把日期欄位序列化為 epoch 秒。[API 契約](agentos-api-contract.md#f07-session-run-filter-contract-2026-11-22)
- [x] **F16 System source retry 與 DB 名稱呈現。** Deployment Retry 只查 health/info，Factory revision Retry 只查 revision；config/model cards 只重查 config（若 config 沒有 models 才呼叫 models fallback）。失敗後保留其他成功來源已載入值，並明確顯示 `/info` error。若 `display_name` 與 DB ID 相同，畫面以說明標示而不重複顯示。這些 UI 變更已包含於本次 production image。
- [x] **F03／F04 Workflow 反向關聯。** Agent／Team 詳情讀 AgentOS Workflow summaries 與每個 Factory Workflow definition，遞迴檢查條件 true／false 與 parallel steps 的穩定 component ID，列出引用該 Agent／Team 的 Workflow name／ID。每個請求可中止；全體載入失敗、definition partial failure、空 Workflow 和查無關聯分開呈現，部分失敗不誤報查無關聯。`ComponentDetails.tsx` 的 TypeScript 與 ESLint 通過。
- [x] **F05 Tree／Graph 與節點關係。** Workflow 頁新增可存取的 Tree／Graph toggle；Graph 依 Factory definition 畫序列連接、Condition true／false 分支及 responsive parallel members。節點 inspector 列 Previous／Next 與平行同組節點，支援點選跳到關係節點並顯示 path/type。`WorkflowExplorer.tsx` 的 TypeScript 與 ESLint 通過；未新增 run highlighting 或 Workflow 執行。
- [x] **F05 未知 step label fallback。** 未知 `step.type` 不再從 `STEP_TYPE_LABELS` 取得空字串；Tree、Graph branch/member、relation cards 和 selected-step inspector 都使用共用 `stepTypeLabel()`，顯示 `Unsupported step (<type>)`。未知型別的 child/執行語義不解析；沒有帶 `loop`／`router`／任意未知 type 的 definition fixture，故只以 production compile 驗證程式，不宣稱 browser 視覺驗收。
- [x] **Same-origin AgentOS proxy。** `routes.ts` 與 System status probe 對本機 AgentOS URL 使用同源 `/api/agentos`；Next route 以 server-only `AGENTOS_URL` 轉送 GET／POST／DELETE，轉送 allowlisted headers、query 與 POST body。Production 不含 proxy Token fallback。此路由解決 ChatGPT browser 對 localhost AgentOS 直接 fetch 連線重設的限制。
- [x] **Production build／Docker runtime。** 由 `agent-ui-delivery/src` 重新產生 `pocs/agno/agent-ui.patch`；Docker Compose build 完成 patch check/apply、Next compile、lint、TypeScript 與 static generation。Image 為 `sha256:813fe12a15be03f9ad5e4ba6b35216412e2a1ad1fe95b6e227c84ffa7d5a94fc`。Docker CLI 複核 `factory-agent-ui` running、port 3000、Compose project `agno-factory-local`；UI container 的 `/` 與 `/api/agentos/health` 回 200，無 Authorization 的 `/api/agentos/workflows` 回 401。Production container 未設定 `AGENTOS_PROXY_AUTH_TOKEN`。AgentOS 3.2.1 與 Agno DB 仍 running，DB healthy。
- [x] **ChatGPT browser feature verification。** 在來源 bind-mount 的 dev UI 以本機 `.env` 授權完成 F03 Testing Agent 的 2 Skills／4 Runtime tools、F04 Knowledge Team 4 個 members 與 Research 返回導覽、F05 Workflow Graph 的 true／false branches、兩組各 3 節點 parallel、Code Proposal 的 Previous／Next／siblings、F07 `FAILED` 本地拒絕、`ERROR` 成功空結果、台北時間範圍轉 UTC 並查到 1 筆 run，以及 F16 外部健康與 Approvals 單卡 Retry。臨時 dev-only Token fallback 與容器已移除；最終 production image 再以未授權 proxy 200／401 邊界驗證。Token 未輸出或寫入文件。
- [x] 本輪 browser 截圖只使用 ChatGPT in-app browser screenshot API，擷取 Knowledge Team、Workflow Graph、System 畫面並於工具輸出目視檢查；沒有擷取整個電腦。工具未提供受支援的 repo 圖檔匯出方式，因此 V05 的 repo 檔案項仍未完成。viewport 設定未生效（`innerWidth` 仍為 1280／1410），本輪 Graph／System 不列為 375px 驗收。
- [x] 新增 2026-11-22 bounded live GET survey：70 個 OpenAPI GET 中 62 個以 read-only request sampling、8 個 content/file/media routes 跳過；狀態彙總為 40×200、13×404、3×422、6×503。Generic unknown IDs／cursor 不能視為路由失效，並已對既有 Agent session 精確補查 runs、detail、checkpoints。完整限制見[API 契約](agentos-api-contract.md#bounded-live-get-sweep-2026-11-22)。

## 尚待資料、服務或裝置能力的項目（2026-11-22）

- AgentOS default 與具名 DB 目前都回傳近期 sessions，沒有成功但空的 Overview sessions fixture；F01 的空狀態尚未驗。
- `/memories`、`/learnings` 都是成功空集合；Knowledge config 回 404，尚無真實 Memory／Learning record 或已配置 Knowledge instance 可驗欄位、分頁及檢索來源。
- 原生 AgentOS `/traces` 與 trace session stats 成功但回 0 筆。Langfuse API 目前可讀到 1 project、14,176 traces，但抽樣 observations 未見 AgentOS run/session key 或 top-level sessionId，故仍無法驗正向 run→trace 關聯；Langfuse datasets 為 0。AgentOS 日誌雖顯示 OTel exporter enabled，不能據此推定目前 traces 由本 POC run 產生。
- FileSystem 四個唯讀 GET 已抽查；Testing Agent `factory-09` 均回 404 `This agent does not have a filesystem`。未指定 scope 的 `/filesystem/files` 回 200／空陣列不等於已配置的空檔案庫。現有 sessions 未見 media key；Media GET 回 503 `Media storage is not configured on AgentOS`，未取得或下載媒體。
- `/os/metrics/users` 因 AgentOS 未設 `user_directory` 回 503；五個其他 metrics 有資料且 UI 已接通。未宣稱 user directory 可以由本 UI 配置。
- F12 已驗 1 個成功 run 的 0% failure、零 runs 的 N/A、明確回傳的 0 token 及無 daily rows 的日期；尚無真實 failed／0%-success run、缺失欄位 fixture 或日期邊界定義。
- 本輪啟動 agno-gateway 與 Backstage：Gateway health/report 為 200，現有報告日期 2026-11-14；Backstage Guest Catalog 有 45 entities，但 Catalog Graph 空白。Langfuse project API 回 1 project，trace API 有 14,176 traces，但沒有已驗 AgentOS run mapping。最新 System image 顯示三個外部 health endpoint 的 status／最後檢查時間，不代表整合關係已配對。
- ChatGPT in-app browser 可擷取並顯示新版畫面，但目前工具沒有受支援的 repo screenshot file output；新 3.2.1 圖片尚無法存入 `docs/screenshots/`。既有舊版圖片沒有改名冒充新版。此次 viewport override 也沒有改變 `innerWidth`，不能當作窄版驗收。
- 實際 125% zoom 仍無法由 ChatGPT in-app browser 設定；2026-11-22 已在 375px current browser 檢查 Runs 控制項／session／run／step 的 Tab 與 Enter，並遍歷側欄九個工作區、以 Enter 切頁、Escape 關閉 drawer 和驗證焦點返回。所有頁面內容的完整 Tab 稽核、graph node inspector、快速 DB 切換與斷線恢復仍待續。最新 image 已以 synthetic Agent stream 驗 endpoint 切換後畫面沒有晚到 callback；未證明 TCP disconnect，也未以真實 AgentOS／模型驗證。
- Overview 已加入 Approvals／Queue 的獨立可用狀態卡；目前兩個授權 GET 都回 503，UI 已明確說明設定不可用且不是成功空集合。F01 仍缺成功空 sessions fixture。
- P3 的 Workflow submit／cancel／continue、approvals、schedules、Knowledge import、Memory/Learning mutation 與 eval-run 尚未實際執行；它們可能建立資料、啟動模型或改變狀態，需有明確的 test target 與影響範圍後再驗。

其餘跨頁工作依 [能力計畫的未完成項目](agent-ui-capability-plan.md)追蹤；OpenAPI 路由存在只算契約盤點，不代表 runtime 已啟用或有資料。

## 歷史接手點（2026-11-22；image `c2f78c7…`，後續已更新）

### F03／F12 覆驗與 production image `c2f78c7…`（歷史 checkpoint；已由 `7fa925d…` 取代）

- [x] Agent 清單搜尋已不分大小寫、去除 query 前後空白，依名稱、ID、model name／ID／provider 比對；Agents／Teams 兩種清單各有對應 placeholder 與 aria label。Docker container 內 typecheck 通過；ESLint 對修改的兩個頁面通過。
- [x] Metrics Runs card 只有在 `total_runs > 0` 且 `success_rate` 是 0–100 有限數值時才顯示 `100 - success_rate`；零 runs 顯示 N/A，缺失／不合法欄位不推算。Legacy Metrics 保留 API 明確回傳的 0 token；欄位缺失或非數字顯示 Not returned，彙總標示 incomplete。日期直接呈現 API 的日期字串，避免瀏覽器時區轉換；預設七日範圍採本地日曆。
- [x] Docker dev container 執行 `pnpm exec tsc --noEmit` 與針對 `AgentExplorer.tsx`、`ObservabilityExplorer.tsx` 的 ESLint，均 exit 0。`pocs/agno/agent-ui.patch` 已從 fork source 更新；production Docker build 的 patch apply、Next compile、lint、TypeScript 與 static generation 均通過。
- [x] 使用 `docker compose -f pocs/agno/docker-compose.yml up -d --no-deps agent-ui` 部署 production image `sha256:c2f78c7b237b203bbfcd5bbbd9c9dbb5651cc94b97d237c05a1a97483eb88ec2`。Docker CLI 確認 UI、AgentOS、Agno DB 均 running 且 Compose project label 為 `agno-factory-local`；UI port 3000，容器內 `GET /` 200；AgentOS image／版本未變，仍為 3.2.1。
- [x] ChatGPT in-app browser 在 375px 驗收：搜尋 `factory-09` 只列 Testing Agent；`MiniMax-M3.1-Flash` 比對出 26 Agents、3 Teams；provider `OpenAI` 也可搜尋，切換至 Teams 時搜尋欄和列表正確切換。Metrics 的 `2026-11-17` 單日回 1 row／1 run、tokens 0、success rate 100%／failure rate 0%；`2026-11-18` 沒有 daily rows，Runs summary 為 0、failure rate 為 N/A。該頁 `innerWidth`、document/body 寬度皆 375px。
- [x] 同一 browser 重驗 Overview 的 Approvals／Queue 各回 503；按 Approvals Retry 只更新 Approvals 檢查時間，Queue 狀態未變。System 顯示 health OK、Agno 3.2.1、26／3／2 元件、1 DB、1 model；Registry 69 筆／7 頁。Langfuse、Gateway、Backstage health checks 各 200；此狀態不代表 trace/project 關聯可用。
- [x] Metrics 初次載入時資料庫選項顯示 `Failed to fetch`；按 UI Refresh 後選項成功出現。瀏覽器沒有提供可核對的失敗 HTTP status，亦未注入 TCP 故障，因此只記為一次暫時性 fetch 錯誤及重試恢復，不推斷原因。
- [x] 新版 Overview、Metrics、System、搜尋畫面使用 ChatGPT 內建瀏覽器 screenshot API 擷取並在工具輸出目視核對；沒有擷取整個電腦。工具沒有提供把影像寫入 repository 的受支援途徑，V05 保持未完成。
- [ ] 尚無真實 failed／0%-success run、缺欄位 Metrics response fixture 或日期邊界規格可供完整驗收；實際 125% zoom 與 repo screenshot file 也未取得。
- [ ] Langfuse 已有 traces 但沒有 dataset，且抽樣 traces 沒有 AgentOS run/session 對應欄位；F11/F13 的正向關聯與 A/B dataset run 仍待具備可追查來源的資料。

### F01 Pending work sources (image `337b6ded…`, superseded)

- [x] Overview 新增 Pending work sources 卡片：對固定唯讀路由 `GET /approvals` 和 `GET /queue` 分別載入、分別 Retry，且 Refresh all 會一起重查。401／403／503 與其他錯誤分開呈現；目前這兩個 Agno 3.2.1 授權 GET 都回 503，卡片清楚顯示「設定不可用，非空結果」。若 route 回 2xx，OpenAPI 沒有清單 schema，因此 UI 不會宣稱待辦數或 0。
- [x] 當時的 production image `sha256:337b6dedeea844d2f56543787c2e974ff2ebdb08fad01fd9c016c47ba93b9de3` 成功套用 patch、Next compile、lint、TypeScript、static generation，後由當時的 `c2f78c7…` image 取代；目前部署已由最上方 `7fa925d…` checkpoint 取代。
- [x] Docker CLI 確認當時 `factory-agent-ui` running、port `3000`，容器內 `GET /` 回 HTTP 200。AgentOS 沒有重啟，維持 3.2.1。
- [x] ChatGPT in-app browser 當時在 `/?view=overview` 顯示 health、runtime info、Factory revision、5 筆近期 Sessions、26／3／2 components；Approvals 和 Queue 各自顯示授權 503 設定不可用。當時 image `c2f78c7…` 的 Retry 覆驗記錄在上方歷史 checkpoint；目前 image 見本文件最上方 `7fa925d…`。
- [x] 窄版 Overview 使用 ChatGPT in-app browser screenshot API 擷取，畫面可見 Pending work sources、兩個 503 說明及各自 Retry。沒有擷取整個電腦；影像僅在當輪 browser tool output，V05 仍開放。
- [ ] AgentOS default 與具名 DB 都有近期 sessions，沒有成功但空的 Overview sessions fixture；不以合成清單冒充真實回應。

### Previous production image `0052fa…` and ChatGPT browser recheck (historical)

- [x] Bind-mounted dev UI 曾出現 Watchpack `ENOMEM` 且 browser 熱更新未能穩定反映 Team 狀態；當時依使用者授權停止 dev container，production build 部署 image `sha256:0052fa5430b7eed45fc2d78eb0e29f04f71c7cb76c57252fb28eb7927`。該 checkpoint 先由 image `337b6ded…`、再由 `c2f78c7…`、最後由目前 `7fa925d…` 取代；AgentOS 未重啟，版本仍為 3.2.1。
- [x] 修正初始化取回 Agents／Teams 後未寫入 Team state 的分支，production browser 授權後顯示 26 Agents／3 Teams（Governance、Knowledge、Observability），System Registry HTTP 200／69 records。
- [x] Registry browser 驗收：預設為 69 records／7 pages；page 2 載入不同 agents；`team` 類型篩選 3 筆；名稱 `Governance` 篩選 1 筆；Clear 還原 69 筆／7 頁。沒有保存 registry names、IDs 或 metadata values。
- [x] F04 production browser 驗收：Observability Team 有 4 members；點 `factory-21` 開 Agent 詳情後，URL 含 `factory_return_team=observability-team`；按 Back 後 URL 還原 Team、清除 return query，4 members 再次顯示。
- [x] 同一 image 在 ChatGPT in-app browser 375×844 viewport 實測 `innerWidth`／document width／body width 均 375px；System／Registry 控制及清單沒有水平溢位。桌面與窄版截圖由 Agent UI browser screenshot API 擷取並在工具輸出目視檢查；API 沒有 repo file export path，因此沒有 `docs/screenshots/` 新圖，也沒有擷取整個電腦桌面。
- [ ] 該次 ChatGPT browser 曾以窄版 viewport 顯示；目前使用的 CUA browser API 不提供 viewport override reset。image `337b6ded…` 的 Overview 與 image `c2f78c7…` 的搜尋、Metrics、Overview、System 已另做 375px 覆驗；125% 瀏覽器縮放仍未實測。現行 image 為 `7fa925d…`，本輪 viewport override 未生效。

### Registry 唯讀面板與 bind-mounted dev loop（2026-11-22；image 439 初次驗收 checkpoint）

- [x] **F17 Registry records UI。** 在 System Explorer 加入 `GET /registry` 唯讀清單，含 type／name 篩選、10 筆分頁、URL query state、Retry，以及 description／provider／model ID／DB ID／toolkit／entrypoint 的白名單摘要；不顯示任意 metadata、不提供寫入，也不提供 DB filter。既有授權 API audit 回 200，總數 69：26 agents、3 teams、2 workflows、27 tools、9 functions、1 model、1 db；`limit=2&page=1` 的 meta 為 35 pages／69 total。沒有記錄 registry names、IDs 或 metadata values。
- [x] **image 439 production/browser 初次驗收（歷史 checkpoint）。** Image `sha256:439a8735afa27ddd42051f57642d045056e17effe2399a95f43b1a964d657a45` 的 built bundle 含 Registry panel。ChatGPT in-app browser 在新 System 分頁顯示清單、type／name filters、pagination；無 Token 時 `GET /registry` 顯示 401／Retry，health 仍為 200，外部 Langfuse／Gateway／Backstage health 各為 200。當時授權後的新面板讀取及篩選尚未驗；後續 0052 image 的授權結果見最上方最新 checkpoint。截圖留在 browser tool output，repo 匯出缺口統一由能力計畫 V05 追蹤。
- [x] **開發時不重建 image。** 新增 [docker-compose.ui-dev.yml](../docker-compose.ui-dev.yml)，以既有 `agno-factory-local-agent-ui` image 的 dependencies 啟動 `next dev`，並將工作樹 `/ui/src` bind mount；Docker inspect 確認 source path 與 localhost port。Next 15.5.18 顯示 Ready。AgentOS CORS 僅允許 port 3000，因此 dev service 使用同一 host port；測試 port 3002 會被 CORS 擋下。掛載版在 ChatGPT browser 的 AgentOS 直接讀取停留 LOADING，未宣稱 dev API 驗收通過。已停止 dev service、還原 production container；image ID 未改、沒有為此流程額外 build。
- **切換命令（從 repo root 執行）：**
  ```powershell
  docker compose -f pocs/agno/docker-compose.yml -f pocs/agno/docker-compose.ui-dev.yml --profile ui-dev stop agent-ui
  docker compose -f pocs/agno/docker-compose.yml -f pocs/agno/docker-compose.ui-dev.yml --profile ui-dev up -d --no-deps agent-ui-dev
  # 開發完成後還原 production container
  docker compose -f pocs/agno/docker-compose.yml -f pocs/agno/docker-compose.ui-dev.yml --profile ui-dev stop agent-ui-dev
  docker compose -f pocs/agno/docker-compose.yml up -d --no-deps agent-ui
  ```
- [x] **image 439 production restore（當時狀態）。** `factory-agent-ui` 曾以 image `sha256:439a8735afa27ddd42051f57642d045056e17effe2399a95f43b1a964d657a45` 啟動，Next production server Ready。ChatGPT browser reload 後 Registry panel 正常顯示無 Token 的 401／Retry；原有使用者分頁的 Token 沒有被讀取或轉移。當時後續 image 0052 為部署；目前部署與覆驗見最上方 `7fa925d…` checkpoint。
- [x] **授權後 Registry 面板驗收。** ChatGPT browser 授權頁在 image `0052fa5430b7eed45fc2d78eb0e29f04f71c7cb76c57252fb28eb7927ade7967` 顯示 69 筆／7 頁；page 2、`team` 3 筆、`Governance` 1 筆及 Clear 還原均已驗。Token 只以遮罩顯示，未記錄或複製 Token 值。
- [x] Registry 新版 System／Registry desktop 與 375px 畫面已由 ChatGPT browser screenshot API 擷取並在工具輸出顯示。repo 圖檔匯出限制統一追蹤於能力計畫 V05。

### image 439 部署與既有瀏覽器分頁核對（2026-11-22；歷史 checkpoint，後由 0052 取代）

- [x] 此 checkpoint 的 Docker 唯讀檢查確認 `factory-agent-ui` 以 `sha256:439a8735afa27ddd42051f57642d045056e17effe2399a95f43b1a964d657a45` 執行，狀態為 `running`，working directory 為 `/ui`。容器日誌顯示 Next.js 15.5.18 `Ready`；編譯 bundle 含 Registry panel。`factory-agent-ui`、`factory-agentos`（`sha256:833882bc…`）及 `factory-agno-db`（`sha256:b0108689…`）三者的 Compose project label 均為 `agno-factory-local`，狀態皆為 `running`。這是較早 image 439 的狀態，不是目前部署。
- [x] ChatGPT browser 現有分頁已顯示 production image `sha256:0052fa5430b7eed45fc2d78eb0e29f04f71c7cb76c57252fb28eb7927ade7967` 的授權 Registry records／filters／pagination；Docker CLI 同步確認 `factory-agent-ui` running 並使用該 image ID。
- [x] Browser screenshot 只在工具輸出顯示；既往 localhost transfer attempt 回報 `fetch failed`，未產生檔案。新一輪只使用 Agent UI browser screenshot API，未再用整桌面截圖；repo 截圖匯出仍待支援路徑。

### F04 Team 成員返回導覽（2026-11-22）

- [x] `AgentExplorer` 現在在 Team 成員開啟 Agent 時，將來源 Team ID 存入 `factory_return_team` query；`ComponentDetails` 顯示 `Back to <Team name>`，點擊後恢復 Team 詳情並清除返回 query。Agents view query allowlist 保留來源 Team，重載可還原返回目標；手動切換元件或類型會清除舊返回狀態。
- [x] 將變更同步到 `pocs/agno/agent-ui.patch`，`git apply --numstat` 可解析整份 patch。使用 bind-mounted dev container `/ui/src` 指向工作樹 `agent-ui-delivery/src`；Next 15.5.18 compiled `/`，`pnpm exec tsc --noEmit` exit 0。沒有重建 image。
- [x] ChatGPT production browser 已點 Observability Team 成員 `factory-21`，進入 Agent 詳情，再按 Back to Observability Team；URL 來源 Team query、返回後 team selection 和 return query 清除均符合預期。dev log 的 Watchpack `ENOMEM` 曾導致使用者授權 production image build；此驗收在 image `sha256:0052fa5430b7eed45fc2d78eb0e29f04f71c7cb76c57252fb28eb7927` 完成，現行 image 見最上方 `7fa925d…` checkpoint。

### 原生 Evals 與深色按鈕覆驗（2026-11-22；image 9d41 checkpoint）

- [x] **F13 原生 Evals 唯讀頁。** 新增 Observability → Evaluations；以 AgentOS 3.2.1 `GET /eval-runs` 實作選定 DB、evaluation type、component type／ID、model ID 與 10 筆分頁，選列後唯讀讀取 `/eval-runs/{id}`。`eval_data`／`eval_input` 預設收合；頁面不提供 create／run，不生成分數。路由及型別在 fork source／`pocs/agno/agent-ui.patch`。
- [x] **3.2.1 live contract 與 UI 驗收。** `GET /eval-runs?limit=10&page=1` 在已授權 AgentOS 回 HTTP 200，0 筆，meta 為 page 1、limit 10、total_pages 0、total_count 0。ChatGPT in-app browser 的最新頁以具名 DB 顯示成功空狀態、Page 1 of 1、空詳情提示及 Langfuse 尚無已驗 dataset run；Token 遮罩。沒有呼叫任何 eval write operation。
- [x] **深色按鈕可讀性修正。** Docker browser 畫面發現預設 primary 樣式的 Filter 按鈕在深色頁面呈淺底且字色不清；Evals、Traces、Metrics、Knowledge 四個 submit action 改用 `outline`。新版 ChatGPT browser 畫面確認 Evals Filter 為深色底、可讀白字。
- [x] **Production build／runtime。** 修正 Evals lint 未使用 import 與錯誤 Retry handler 後，Docker `pnpm build` 的 Next compile、lint、TypeScript、static generation 全數通過；button style 修正後再次完成相同 build、Compose recreate 及 health wait。此 checkpoint UI image 為 `sha256:9d41d8585e5e3828a11217bd638589789df10529278eb06539001f8ceb20f245`；後續 Registry panel image ID 見上方最新 checkpoint。
- [x] Evals 畫面已在 ChatGPT browser tool output 擷取與檢視；repo 圖檔匯出限制統一追蹤於能力計畫 V05。原生 eval DB 成功空集合，Langfuse dataset／A/B 的 run、score、reason 或 Trace 關聯仍待真實 dataset run。

- [x] **F16 System 外部健康探測。** 新增同源 `GET /api/integrations/status`，由 Agent UI 容器透過 Compose network 對 Langfuse `/api/public/health`、Gateway `/health`、Backstage `/healthcheck` 做固定的唯讀 GET；response 只回傳 endpoint ID、HTTP status 或通用 request error、檢查時間，不讀取服務回應本文，也不接受 caller-supplied URL。System Explorer 顯示三項狀態／最後檢查時間，Refresh all 會重查；request error 時可 Retry。容器內與 ChatGPT browser UI 均驗出三端 HTTP 200；Backstage Catalog entities API 未登入時回 401，Catalog Graph 仍空白。Langfuse project／trace correlation 未驗。
- [x] **F14／F15／F17 管理路由狀態（image 3e55 歷史 checkpoint）。** System 對 `/approvals`、`/schedules`、`/components`、`/queue`、`/service-accounts`、`/registry` 各做獨立唯讀 status check，response records 不載入。Image `336c9a8…` 的授權 UI 顯示前五路由 503、Registry 200；image `3e55f72…` 無 Token 時六路由各為 401。新 UI 每個 route 都有 Recheck；點 Approvals 後只更新該列時間，其他五列時間保持不變。管理 records 尚無可用 UI／配置證據；image 0052 的授權 Registry list 及本輪 c2f78c7 System 覆驗見最上方。
- [x] **使用者輸入 Token 後的系統資料覆驗。** ChatGPT browser 的 Auth Token 欄位只顯示遮罩；System 成功顯示 health OK、Agno 3.2.1、26 Agents／3 Teams／2 Workflows、Factory revision、1 session DB、1 model、0 interfaces。此結果在 image `336c9a8…` 完成；新 image `3e55f72…` 保留相同資料來源呼叫並加入管理路由獨立 Recheck。沒有讀取、抄錄或輸出 Token 值。
- [x] **F16 external-health build/runtime checkpoint (historical).** Image `sha256:3e55f721286f3e9b0383d0447e43d323e92eab0a1c65a87e57d93900886f843c` 已由 Compose build／部署；Agent UI 與 AgentOS 容器皆 running，AgentOS 為 3.2.1／image `sha256:833882bc1e024e1acbc6ad9ce953c5b4b1bb0239451ea85f28a1ab17f8b013f2`。同源 status API 在容器回 200 並只含三項 status metadata。這是後續 Evals 修正前的 image。
- [x] **Targeted live GET contract audit.** 依照本機既有驗收授權的 3.2.1 route 結果，補記管理端點授權後 503、Knowledge no-DB 503／selected-DB 404、Registry page 2、filter schemas、空的 eval/trace/memory/learnings 與 metrics status；另以 no-Authorization GET 確認 `/health` 為 200、9 個受保護路由為 401。逐路由分組、計數及限制見[API 契約](agentos-api-contract.md#321-targeted-read-only-get-audit-2026-11-22)。此為唯讀抽查，不是全 135 operations 驗收。
- [x] **V04b 外部服務連線與報告入口。** 依計畫啟動 `agno-gateway`、Backstage、Langfuse worker；Langfuse web／worker 及相依服務均在 running，`GET /api/public/health` 回 200／3.227.1，AgentOS log 有 `Langfuse OTel tracing enabled`。Gateway `GET /health` 回 200，`GET /report` 回 200，頁面標題 `PAY-482 · Workflow 執行報告`、報告日期 2026-11-14。Backstage Guest Catalog 顯示 45 entities（26 Agents／3 Teams／2 Workflows／14 Skills）；Catalog Graph 畫布仍空白。Langfuse UI 要求登入，project／trace 關聯未核對；沒有呼叫模型或建立新 run。完整限定見[驗收證據](agent-ui-verification-evidence.md)。
- [x] **image 780 Overview 窄版基線。** ChatGPT in-app browser 載入 image `sha256:7809386…`，以 375×844、300×675 CSS viewport 觀察 Overview；document/body scroll width 分別為 375px、300px，無水平溢位，`/health` 顯示 OK，Factory／sessions／components 仍以獨立 401／Retry 呈現。兩張圖於該輪 browser tool output 顯示；這不是本次新增的 System panel 窄版覆驗。
- [x] **最新 System 授權覆驗。** production image `sha256:0052fa5430b7eed45fc2d78eb0e29f04f71c7cb76c57252fb28eb7927ade7967` 的 ChatGPT browser System 顯示授權 Registry panel 69 筆／7 頁；desktop 與 375px 畫面已直接由 browser screenshot API 擷取並目視檢查。
- [x] System 新版畫面已在 ChatGPT browser tool output 擷取與目視檢查；repo 圖檔匯出限制統一追蹤於能力計畫 V05。
- [x] **Docker／build／runtime 複核。** 依使用者要求直接用 Docker CLI 操作。最新 `factory-agent-ui` 使用 image `sha256:0052fa5430b7eed45fc2d78eb0e29f04f71c7cb76c57252fb28eb7927ade7967` 且為 `running`，port `3000`；`factory-agentos` 使用 `cletus/agno-agentos:3.2.1`、image ID `sha256:833882bc1e024e1acbc6ad9ce953c5b4b1bb0239451ea85f28a1ab17f8b013f2`。AgentOS `/health` 回 HTTP 200，OpenAPI 為 94 paths／135 operations 且有 `/factory/catalog`。本次 UI production build patch apply、Next compile、lint、TypeScript 與 static generation 完成。沒有新增或執行程式測試。
- [x] **單路由 Recheck 驗收（image 3e55 歷史 checkpoint）。** ChatGPT browser 無 Token 頁面上，按 Approvals 的 `Recheck` 後 HTTP 401 保持；該列時間從 `12:59:02` 改為 `12:59:28`，Schedules、Components、Queue、Service accounts、Registry 五列的時間仍為 `12:59:02`。此操作只重送 Approvals GET，不載入 records。
- [x] **image 3e55 browser／container 複核（歷史 checkpoint）。** 使用者輸入 Token 的 ChatGPT browser 分頁在 image `336c9a8…` 載入 AgentOS 3.2.1、26 Agents／3 Teams／2 Workflows、revision、1 DB、1 model、0 interfaces；管理路由前五項為 503、Registry 為 200。image `3e55f72…` 分頁未輸入 Token，System 顯示受保護路由 401 與三項外部 health 200。Docker inspect 顯示 Agent UI／AgentOS running，image IDs 分別為 `sha256:3e55f721286f3e9b0383d0447e43d323e92eab0a1c65a87e57d93900886f843c`、`sha256:833882bc1e024e1acbc6ad9ce953c5b4b1bb0239451ea85f28a1ab17f8b013f2`；`GET /api/integrations/status` 只含三個 status／timestamp，皆 HTTP 200。該 checkpoint 截圖顯示於 browser tool output；repo 匯出限制見 V05。本輪 c2f78c7 結果以最上方 checkpoint 為準。
- [x] **P1.1 Factory／runtime detail 404 降級與 Retry。** 以本機合成 AgentOS fixture 驗 Factory definition 404／runtime 200，以及 Factory definition 200／runtime 404 兩種局部失敗。各自按 Retry 後只重送失敗來源：`/factory/agents/factory-404` 計數 1→2、`/agents/factory-404` 維持 1；`/agents/runtime-404` 計數 1→2、`/factory/agents/runtime-404` 維持 1。成功來源 JSON 仍顯示。故障注入不需要或使用 OS Token，資料均為合成內容。
- [x] **Sidebar 初始化請求去重。** 修正初始化 effect 對每次 render 的 `initialize` callback identity 與 Chat mode 的依賴；改由 endpoint／Token／persist hydration 觸發，並以 ref 呼叫最新 callback。切到本機合成 endpoint 後 `/health`、`/teams`、`/agents` 各只請求一次，沒有重複初始化風暴。
- [x] **過期 Agent deep link 保留。** `factory_id` 存在時保留 query ID 並載入詳情，不再因 ID 不在清單而靜默選取第一個 Agent。新 image 用真實本機 UI 開 `codex-verification-missing-agent`；因沒有 Token，Factory/runtime 兩個端點都回 401，但詳情仍保留指定 ID。404 UI 行為由上述合成 fixture 驗證。
- [x] **F01 reload、DB 與 URL state。** Overview `overview_db=<具名 DB>` reload 後仍選回同一 DB；因 Token 僅在瀏覽器記憶體，reload 後需依既有授權重新輸入，之後 Factory revision、26 Agents／3 Teams／2 Workflows 與 5 筆 sessions 均載入。由 Runs 點 Overview 後 URL 只保留 `view=overview` 和 `overview_db`，移除舊 session/run/component/agent/db filters；瀏覽器 Back 恢復 Continuous Improvement Workflow 的 session `ffea1d9d-aad6-4030-b68c-cfb4192b429c`、run `5898977d-3a48-4af6-a0a8-12e618b78724`、具名 DB 與完成狀態。AgentOS default 與具名 DB 此次都回傳近期 sessions，沒有成功空清單 fixture。
- [x] **F01 逐來源 Retry 與故障隔離。** 清除 Token 後 Factory revision、Recent sessions、Registered components 各自顯示 401 與 Retry，health／runtime info 仍維持成功；分別點擊三個 Retry 後各卡仍回報 401，其他來源繼續可見。重新輸入本機 Token 後三個來源重新載入成功。Factory／config 卡在 error 時同時保留上次成功內容並標示錯誤狀態與最後檢查時間。
- [x] **F01 per-view URL cleanup。** 最新 patch 為各 view 定義 query allowlist 和清理集合。從 Runs 切到 Overview 後 URL 只留 `view=overview` 與所選 `overview_db`；Browser Back 還原原 session／run／DB detail。Runs 切到 System 後為 `?view=system`，等 `/config` 等資料 hydration 後仍保持不含舊 `agent`／`db_id` query。這項修正避免 stale Chat／Runs URL state 在載入完成後重新污染另一個 view。
- [x] **F06 Tools／Skills／Models 目錄。** Tools 頁由 AgentOS `/config` 的 29 個 components 完整載入 108 個 Runtime tools，顯示來源種類／ID、endpoint、tool identity 和可展開 schema。以 Testing 搜尋顯示 4 個工具，全部 schema 可展開；`load_work_item_context` 有 4 properties 且 `work_id` 必填。Factory `/factory/catalog` 快照含 14 個 Skills、instructions 與所有 Agent references；`model-usage-cost` 列出 Optimization／factory-19、Cost Control／factory-27，點擊後正確選取 Cost Control。Models 由 `/config.available_models` 載入 1 個 `MiniMax-M3.1-Flash`／OpenAI，並回列 29 個引用元件；額外 model parameters 沒有從 API 回傳，`GET /models` 在 3.2.1 為 404。
- [x] **375px 資料頁覆驗。** 將 ChatGPT in-app browser viewport 設為 375×844，Overview、Runs、Tools、Skills、Models、Observability Metrics、System 均完成檢查；System 也在有效 Token 與無 Token 401 狀態檢查。document/body 寬度為 375px；Overview 主內容 client／scroll 寬 334px；Runs 與 Tools／Skills／Models 約 323px；Observability metrics 約 263px。長 Skill 與 Agent reference 仍在卡片內換行。此輪資料／目錄驗收對應 image `sha256:8f126975d3f2ac3f600f30604607996f16c63c2e0edd5054eb835bdac570feff`，後續部署 image `sha256:4f57e9…` 保留相同功能並加上 Sidebar 鍵盤收合；前一 image `sha256:bab1260…` 加入 endpoint 切換隔離；最終 image `sha256:7809386…` 修正初始化觸發並保留該隔離行為。
- [x] **窄版 Sidebar Escape、背景與焦點返回。** 前一 image `sha256:bab1260eaeef52e25c46cea6f600fdb9a8fa1da1382bddb2bafea2ad73a43433` 新增／保留 compact overlay 開啟時的 Escape handler；Esc、點抽屜外背景、選取 Tools view 後都會收合導覽並把焦點設回 `Expand sidebar`。在 ChatGPT in-app browser 的 300×675 CSS viewport（375×844 的 125% zoom 尺寸代理）重驗，document/body 寬 300px、各工作區 main client／scroll 寬 248–259px，無水平溢位。此尺寸不代表實際瀏覽器 zoom；完整跨頁 Tab 順序與關閉詳情焦點流程尚未完成。
- [x] **Sidebar 鍵盤導覽補驗。** 前一 image `bab1260…` 的 300×675 compact drawer 中，由 `Collapse sidebar` 按 Tab 到 Overview，再按五次 Tab 到 Tools 後按 Enter，URL 變為 `?view=tools`、drawer 收合，`document.activeElement` 回到 `Expand sidebar`；按 Escape 與點抽屜外背景也收合並返回焦點。跨頁完整 Tab 順序與關閉詳情焦點返回仍未驗。
- [x] **F12 operational metrics live contract 與 UI。** Docker AgentOS `GET /os/metrics/latency|models|runs|sessions|tokens|users` 共六個 GET operation；UI 按所選日期區間請求，支援 DB 的 metrics 傳 `db_id`。實際回應：latency／runs／sessions／tokens 各 8 筆日資料、models 1 筆；users 為 HTTP 503，detail 明確要求替 AgentOS 傳入 `user_directory`。Observability → Metrics 已整合六張來源獨立卡，分開顯示 loading／錯誤／Retry；users 只顯示安全的筆數（若可用），不列個人資料。legacy `/metrics` 仍保留原有 DB／table／日期查詢。畫面在本輪 ChatGPT in-app browser tool output 擷取與目視確認，沒有 repo 圖檔。
- [x] **外部服務淺層健康檢查。** 只讀取本機 Langfuse `GET http://127.0.0.1:3001/api/public/health` 得 HTTP 200；只記為 health endpoint reachable，沒有推論已連結 project、OTel exporter 或 trace。當時未見 agno-gateway container；Backstage／報告服務狀態未配置或未驗。
- [x] **image 8f 的 375px Overview 資料驗收。** 使用 ChatGPT in-app browser 以 375×844 重新載入部署後頁面；具名 `overview_db` 保留，資料載入後顯示 AgentOS 3.2.1、health OK、26 Agents／3 Teams／2 Workflows、Factory revision 與 5 筆近期 sessions。`innerWidth`、document/body scroll width 均 375px；主內容 client／scroll 寬 334px。新版畫面已在 browser tool output 擷取並目視確認；最新 image bab 另做 375／300px 九個工作區無 Token 窄版覆驗。
- [x] **前一 image 全工作區窄版覆驗。** `sha256:bab1260eaeef52e25c46cea6f600fdb9a8fa1da1382bddb2bafea2ad73a43433` 在 ChatGPT in-app browser 以 375×844 及 300×675 viewport 依序切換 Overview、Chat、Workflows、Agents、Runs、Tools、Data、Observability、System。兩種尺寸的 `innerWidth`／document／body 寬一致；375px main 寬 323–334px，300px main 寬 248–259px，沒有水平溢位。System 的 health／runtime 仍可讀，無 Token 的受保護來源各自顯示 401／Retry。實際瀏覽器 125% zoom 仍未設定；新 screenshot 只顯示於 browser tool output，沒有 repo 檔案。
- [x] **P0.4 endpoint 切換與晚到畫面更新隔離（synthetic fixture）。** `Sidebar` endpoint change 會 abort active stream 與初始化讀取，清空 Token、Agent／Team／session／message 快取、model 和 endpoint-bound query。前一 image `bab1260…` 的 ChatGPT in-app browser 測試以 synthetic Token、DB/table filter 和不可用 loopback endpoint 切換：Token 清為 `NO TOKEN SET`，URL 清為 `?view=observability`；本輪最新 image 使用 synthetic Agent fixture，未切換 endpoint 的控制組收到並顯示 `late-fixture-marker`；第二次 `/agents/{id}/runs` 的 `RunStarted` 送達後立即切到另一 loopback endpoint，10 秒後 fixture 雖嘗試送 late marker，UI 仍是空白新聊天。計數器為兩次 POST、兩次 late write attempt、零次捕捉到 disconnect；因沒有 callback instrumentation，只能確認切換後畫面沒有 late marker，不能斷言 callback 未被呼叫、TCP 中止或真實 AgentOS／模型 stream 已驗。已還原 `http://localhost:7777`，Token 保持 `NO TOKEN SET`。取得 `.env` key 的額外 loopback bridge 遭 browser auto-review 拒絕，沒有憑證回到瀏覽器或輸出。request-log UI／紀錄隔離仍待驗。
- [x] **最新 query allowlist 覆驗。** 新 image 在前一輪實測的 Observability → System 後，URL 為 `?view=system`，資料 hydration 後不帶舊 `agent`／`db_id`；System → Tools 為 `?view=tools`。Sidebar 為九種 view 設定各自可保留的 query key。深連結全欄位及不存在 ID 的跨頁回歸仍待驗。
- [x] **System 無 Token 來源隔離。** 375px System 頁清除 Token 後，config、Factory catalog、session storage、models、interfaces 各自顯示 401／Retry；health/runtime 資料仍成功顯示，外部 integrations 保持 `NOT CHECKED`，沒有把 AgentOS 內部狀態推斷成外部服務健康。
- [x] **Docker image／production build。** 首輪在既有 source patch 中修正 Sidebar named/default export、Sidebar barrel named import 和 unified diff hunk 行數後，Docker production build 成功完成 patch apply、Next compile、lint、TypeScript 與 static generation；部署後以 Docker inspect 確認上述最新 image 運行。
- [x] **Factory catalog live API contract。** Docker 內 `/openapi.json` 為 94 paths／135 operations，含 `GET /factory/catalog`。該路由回傳 complete Factory snapshot、revision、Skills 及 Agent IDs／names；OpenAPI operation 未宣告 `security`，但 Docker 內無 Authorization 的實際 request 回 401，延續 AgentOS runtime middleware 認證。
- [x] **Docker Compose port cleanup。** 為排查重開機後 host `localhost:7777` 轉送問題而暫用的 loopback `17777` override 已移除；用 base Compose file 只 recreate `factory-agentos`，health check 回 healthy，live OpenAPI 仍為 94／135 且 `/factory/catalog` 存在。AgentOS 僅保留 Compose 原本的 port `7777`，資料 DB 與 Langfuse services 未重建。
- [x] **image 3e55 畫面截取（歷史 checkpoint）。** ChatGPT in-app browser 擷取並檢視 1280×720 System management／external status cards，顯示六項 AgentOS route 401 與 Langfuse／Gateway／Backstage 200；畫面在 browser tool output 可見。該圖未保存至 repo，因工具沒有受支援的 screenshot file output；image 0052 的 System／Registry、image c2f78c7 畫面與現行 image 3c14db1 reload 截圖分別列於本文件對應 checkpoint，repo 匯出限制見 V05。
- [ ] **仍待續。** Overview 成功但空 session 清單需合適 DB fixture，且尚未提供待處理項目卡片／Approvals／Queue 來源原因；實際 125% zoom、跨頁完整 Tab 順序／Workflow graph node 鍵盤操作／詳情焦點返回、快速 DB 切換與斷線恢復仍未驗；真實 AgentOS／模型 stream abort 與 request-log 隔離也未驗。新版 screenshot repo 匯出仍缺受支援 file API。F07 非空 compaction 與 P2.1 Knowledge／Memory／Learnings、P2.2 Trace 正向關聯需真實資料；Langfuse project／trace 關聯需登入與實際 run；Backstage Catalog Graph 仍無節點。P1.1 Factory／runtime 404 Retry 已由合成 fixture 驗收，不列待辦。P0.3 靜態 OpenAPI mapping 與 P2.4 tag-family 盤點已完成；runtime operation sampling 與外部整合缺口仍開放。其餘依[能力計畫](agent-ui-capability-plan.md)追蹤。

## 2026-11-21 接手點（歷史 checkpoint）

本節記錄較早的工作狀態。以下未勾選框只表示 2026-11-21 checkpoint 當時尚未完成；目前狀態以本文件最上方 checkpoint 與能力計畫為準。

- [ ] **未完成功能續作（2026-11-21）。** 使用者要求繼續完成能力計畫中的未完成項，且每段進度需落盤。已讀取 Serena instruction manual 並核對 3.2.1 checklist；接續範圍含 F01～F17 部分未交付家族、通用深連結、API 逐頁對照、失敗恢復、窄版／鍵盤驗收及 P3 操作評估。F08、Approvals、Knowledge 寫入、Memory 修改、Metrics refresh、eval run 可能啟動 Agent、寫入資料或觸發成本，實作前依計畫明確操作授權要求處理。先從唯讀且資料來源可確認的工作開始，每完成一片就更新此 checkpoint 與 capability checklist。
- [x] **Docker／工作樹起點檢查。** 本工作樹有先前留下的多個 POC 修改、workflow fixtures、screenshots 及 scenario 變更，已原樣保留。以受審查的 Docker 權限成功讀取 Compose 狀態：agent-ui、agentos、agno-db 與 Langfuse services 正在執行；Postgres、Clickhouse、MinIO、Redis healthchecks healthy。AgentOS image 為已部署 3.2.1 tag，UI image 是已驗的本機 image ID。這是建置前起點，不代表新版 UI 已完成驗收。
- [x] **F01 `/sessions` 契約確認。** 使用 Compose 內 AgentOS 現行 Bearer key 作只讀查詢，`GET /sessions?limit=2&page=1` 回 HTTP 200，根欄位 `data`／`meta`，第一頁 2 筆、總數 47、總頁數 24。記錄的 session 欄位名和型別包含 `session_id`／string、`session_name`／string、`session_state`／object、`created_at`／ISO string、`updated_at`／ISO string、`session_type`／string、`workflow_id`／string 及 metrics／metadata。查詢未輸出 session ID、key 或內文。Dashboard 可用這個端點呈現近期 sessions 作最近 runs 的入口。
- [x] **F01 Overview source slice 實作。** `agent-ui.patch` 新增 Overview route 和 sidebar 項目，沒有 `view` 且未指定舊 Chat agent／team／session 時開總覽。頁面分開載入 `/health`、`/info`、白名單 `/config`、Factory revision、`/sessions`，各有獨立 error／Retry；最近 5 sessions 按 `updated_at` 排序，可用已配置 DB 篩選，導向 Runs 時保留 type。`overview_db` query 還原 DB 選擇。暫不宣稱已通過 Docker build 或瀏覽器驗收。
- [x] **Docker patch 行尾診斷。** 第一次建置在 fork commit `817a009b3d7e407b17b48872f5bbf1c5055b5955` 的 `git apply --check` 因 Windows CRLF patch 行尾失敗。以同 image 的暫時性 container reset 到 base commit，CRLF 檔失敗、轉 LF 後相同 patch 的 `git apply --check` 通過。已把唯一的 `pocs/agno/agent-ui.patch` 正規化為 LF，未改動 UI／AgentOS 正在執行的 containers。重跑完整 Docker build 待續。
- [x] **Overview 首次 production build 診斷。** LF 正規化後 Docker 的 `git apply --check` 和 patch apply 成功。Next compile 發現 Overview 新增 `RunExplorer` import 缺少結尾引號；已修正 patch。TypeScript、lint／production build 正在重新驗證。
- [x] **Overview production build。** `docker compose -f docker-compose.yml build agent-ui` 成功；Docker 套用 LF patch，Next production build 與 typecheck 通過，image 為 `sha256:1bf26cc267b82b446533d6a610d248ff9db757757ca3b6e6aa7f0829a9189d41`。本次 build 使用 BuildKit cache，因此不代表重新執行每個編譯步驟；先前同一份 patch 曾經執行到 compile/typecheck 並修復對應錯誤。
- [x] **Overview 部署及核心資料驗收。** `factory-agent-ui` 已以新 image `sha256:1bf26cc267b82b446533d6a610d248ff9db757757ca3b6e6aa7f0829a9189d41` 重新建立並執行，`http://127.0.0.1:3000/` 可載入 Overview。使用者在本機頁面更新 Token 後，真實資料載入：AgentOS 3.2.1／health OK、26 Agents、3 Teams、2 Workflows、Factory revision `bdcc8db58b2161b3`、1 session DB、近期 5 sessions。Token 僅顯示遮罩，未讀出或記錄值。初次無 Token 時 Factory revision、config、sessions 各自顯示 401，health/info 仍成功；錯誤畫面有逐來源 Retry。舊 Chat URL 含 `agent=sdlc-ticket-agent` 時仍開 Chat，Overview 可由側欄直達。
- [x] **Overview 375px layout 檢查。** ChatGPT in-app browser 明確設為 `375×844`；`innerWidth=375`、document／body `scrollWidth=375`，無水平溢位。頁首、Agents／Teams／Workflows／Recent sessions cards 直向排列；側欄縮成圖示列。截圖已在驗收工具輸出目視確認；瀏覽器安全策略阻擋將截圖另存成 repo 檔案，因此不以舊圖冒充本次證據。
- [x] **F01 Overview 首輪待驗項目（2026-11-21；已由 2026-11-22 覆驗更新）。** 當時待驗的 DB reload、canonical URL／Browser Back、逐來源 Retry／恢復與 Factory/runtime 404 局部降級，均已於本文件上方及新版驗收證據完成。成功空 sessions fixture 與 Overview 待處理項目來源狀態仍待續；新版圖檔另由能力計畫 V05 追蹤。
- [x] **F01 精確 Session 深連結 Docker build 與 browser 驗收。** `agent-ui.patch` 從 type 對應 `agent_id`／`team_id`／`workflow_id` 為 component ID；近期 session 缺名稱時用 `Untitled session`，名稱最多兩行；`Open session` 帶 `view=runs`、type、component ID、session ID 及有效 DB。完整 Docker production build、lint／typecheck、static page generation 通過；部署 image `sha256:2d3a9e94cb3231bdede9cbefb17bc753e068477fa439ce527ea9754624afde93`。ChatGPT in-app browser 實際載入指定 Workflow session 和其 1 個 `COMPLETED` run；Workflow、session／run IDs 與 URL 一致。從具名 DB 切為 `AgentOS default` 後以近期 session 入口重開，Runs URL 不含 `db_id`、保留 `overview_db=default`，同一 session／run 仍可載入。此驗收 viewport 為 375px，document 寬度 375px，無水平溢位。
- [x] **本輪 Docker runtime 複核。** 唯讀 `docker inspect` 確認 `/factory-agent-ui` 狀態 `running`、image 為上述 `sha256:2d3a9e94cb3231bdede9cbefb17bc753e068477fa439ce527ea9754624afde93`；`/factory-agentos` 的設定 image 是 `cletus/agno-agentos:3.2.1`。沒有變更、重啟或停止容器。
- [x] **Overview 375px 截圖目視檢查。** `ChatGPT in-app browser` 擷取的 375×844 畫面已在工具輸出檢視，顯示四張摘要卡直排、健康區塊可讀、無水平溢位。嘗試另存時瀏覽器安全策略拒絕非 HTTP(S) URL；依政策停止該傳輸方式，沒有使用替代瀏覽器或間接注入。截圖目前只在本次工具輸出，不存在 repo 圖檔；需另有受支援的 screenshot file delivery API 才能補存。
- [x] **F01 URL state 歷史觀察（已解決）。** 早期 Runs → Overview 留下舊 query 的情況，已由後續 per-view allowlist 修正；canonical Overview URL、reload 和 Browser Back 的目前驗收見上方 F01 checkpoint。
- [x] **F06 runtime tool parameters（契約確認，2026-11-21）。** 只讀 Docker query `GET /agents/factory-09` 回 200；Testing Agent 有 4 個 tools，回應每個 tool 含 `name`、`description`、`parameters`；parameters schema 的 top-level keys 為 `type`、`properties`、`required`。UI 現有卡片只顯示 name／description，底下 raw runtime JSON 可查看完整資料；API 摘要只記 schema keys／property names，未輸出使用者參數值、prompt 或 Token。
- [x] **F06 tool schema Docker/browser 驗收。** 新 image `sha256:47aa9b0583a5a73e3b66113f1394fe91b0bd2fd2f8a2d9aab5182395eb29b8a3` 已部署；AgentOS 容器仍使用 `cletus/agno-agentos:3.2.1`。ChatGPT in-app browser 在 3.2.1 runtime 選到 Testing Agent `factory-09`，看到 4 個 Runtime tools 及各自的 `Parameter schema` disclosures；展開 `load_work_item_context` 後實際顯示 object type、4 個 properties 和 `work_id` required。375×844 下 document／body 寬度均 375px；schema pre 的 client／scroll width 均 237px，只有預期的 schema 內垂直捲動。截圖已於工具輸出呈現，尚未成為 repo 圖檔（瀏覽器安全策略不允許現有另存管道）。
- [x] **Docker 資源清理。** 新 `factory-agent-ui` 為 `running` 且使用 `sha256:47aa9b0583a5a73e3b66113f1394fe91b0bd2fd2f8a2d9aab5182395eb29b8a3`；舊 UI image `sha256:2d3a9e94cb3231bdede9cbefb17bc753e068477fa439ce527ea9754624afde93` 經 `docker ps -a --filter ancestor=...` 確認無 container 引用後已刪除。Agno `3.2.1` AgentOS 保持 running。一次性 source 容器及本輪兩個暫存 source 檔均已清理；沒有移除其他 image／volume／container。
- [x] **F06 驗收 Token 復原。** 重建 UI 後記憶體 Token 清除；瀏覽器讀回舊 password input 時回傳 `<redacted>` 佔位字串，錯誤值觸發 401 後立即清除。瀏覽器隔離剪貼簿阻止安全自動貼回；使用者在本機 UI 手動重新輸入後，健康的 Workflow Runs 與 Agent 詳情恢復。Token 只以遮罩顯示，未記錄 key。
- [x] **F01 深連結首輪 build 型別診斷。** Patch apply 和 Next compile 通過；TypeScript 指出 Overview 讀取 `runDbId` 但只宣告 setter。已補成 state／setter 並重算 unified diff hunk；首輪失敗 image 未部署，第二次 build 已成功。

- [x] 已將 [Agent UI 能力計畫](agent-ui-capability-plan.md) 同步至 3.2.1，更新 Compose、API 契約、模型來源、session compactions 與接手位置。用子項標記已完成的契約盤點及驗收，修正新版驗收證據的章節連結，保留其餘功能、375px 覆驗與新版截圖待辦。本次只更新文件。
- [x] 目前 Agent UI image `sha256:36cb2655b9c86b34613f865b39d29dda4c190c71a530a67d0225f73c6c26c190`、AgentOS image `sha256:833882bc1e024e1acbc6ad9ce953c5b4b1bb0239451ea85f28a1ab17f8b013f2` 均以 Docker 執行；AgentOS 版本 3.2.1、healthcheck healthy。
- [x] `cletus/agno-agentos:3.2.1` 已發布至公開 Docker Hub，manifest digest `sha256:6a13d301661dcef023c1d7d0d5264cd369a68c1cca4cb362698ba6749e77df70`；Compose 預設不建置 AgentOS，改用公開 image；本機 build overlay 是 `docker-compose.build.yml`。
- [x] 運行中的 3.2.1 API 檢查：`/info` 200／version 3.2.1、`/config` 200／1 available model、`/openapi.json` 200／93 paths／134 operations、Workflow session compactions 200／empty array；v3 沒有 `/models`，UI 使用 config models 並保留 v2 fallback。
- [x] 3.2.1 的全部 134 個 OpenAPI operations 已由 live container 產生唯讀 inventory：[route、parameters、schema references 與 security declaration](agentos-api-openapi-3.2.1.md)。
- [x] ChatGPT in-app browser System Explorer 顯示健康、版本、26 Agents、3 Teams、2 Workflows、DB、model、Factory revision，Token 遮罩。3.2.1 screenshot 已在 browser tool output 目視核對，但沒有存成 repo image；375px System／Runs 尚未用有效 viewport override 驗證。見[新版證據](agent-ui-verification-evidence.md#agno-321-ui-verification)。
- [x] 清除本次建立且無 container 使用的舊 image：舊 Agno 2.9.0 與 11 個舊 Agent UI images、錯誤 `cletuslee/agno-agentos:3.2.1` 本機 alias；保留目前 UI、AgentOS images，不動其他專案 images、containers 或 volumes。`pocs/agno/.uv-cache` 已刪除。
- [x] 歷史 UI image `sha256:1a182c1c701b30c0ba4e1b6013585e479323623837f7dde26d32fdf95f86ebd1` 已在 3.2.1 通過後確認無 container 引用並移除，不再當作目前 image。
- [x] 使用者明確授權我直接從本機 `pocs/agno/.env` 讀取 `OS_SECURITY_KEY` 並用於本機 Agent UI，後續不需再次詢問。Token 只在瀏覽器記憶體內使用，欄位遮罩；未列印或存進文件／截圖。重載先顯示 `NO TOKEN SET`，恢復後 UI 可讀 API。
- [x] 375px Chat welcome heading 可換行、輸入框留在畫面內；側欄展開為 overlay drawer，不壓縮 Workflow 主欄。抽屜有明確收合按鈕；背景點擊與選工作區後收合已接上程式，但尚未分開手動點測。證據：[Chat 窄版](screenshots/chat-welcome-375px-after-fix.jpg)、[抽屜開啟](screenshots/workflow-sidebar-drawer-open-375px.jpg)。
- [x] 新版 Workflow 頁載入 revision `bdcc8db58b2161b3`；Software Delivery 顯示 22 steps、11 agents、1 team。375px Parallel Verification 的 Testing／Security／Reliability 卡片可讀，見[窄版 Workflow](screenshots/workflow-parallel-verification-375px-after-drawer-fix.jpg)。
- [x] 375px Testing Agent 詳情可讀 Factory role、summary、inputs／outputs、2 skills、model、4 runtime tools；Full Factory definition、instructions、Full AgentOS runtime JSON 均可展開。截圖：[Agent 詳情](screenshots/agent-testing-details-375px-after-drawer-fix.jpg) · [Runtime JSON](screenshots/agent-testing-runtime-375px-after-drawer-fix.jpg)。
- [x] Sessions 401 錯誤顯示 `AgentOS returned 401 Unauthorized` 與 Retry；恢復 Token 後載入 7 筆 sessions。證據：[Sessions 401／Retry](screenshots/sessions-401-retry-drawer-375px.jpg)。
- [x] Runs Explorer 目前涵蓋 Agent／Team／Workflow 三種 session type：Agent 7 sessions；Observability Team 1 session／5 runs；Software Delivery Workflow 13 sessions／3 頁。已驗成功空資料 200、無 Token 401／Retry、型別專屬 run detail。每種狀態均有 375px 截圖，見[證據文件](agent-ui-verification-evidence.md)。
- [x] Runs DB selector 從唯讀 `/config.session.dbs[].db_id` 載入可選項，並合併元件清單的 `db_id`；「AgentOS default」移除 URL filter，選具名 DB 會設定 `db_id` 並重查 Sessions／Runs。清單 API 錯誤時保留預設查詢並顯示獨立提示。
- [x] DB selector 實際瀏覽器驗收：AgentOS config 有 1 個 session DB；375px 與 1280px 可讀顯示；切至 default 時 `db_id` query 移除且 Workflow session 仍有資料；切回具名 DB 後 Agent 仍載入 7 sessions；重載後 `db_id` 保留，重新授權後 Runs 仍按該 DB 載入。畫面見[驗收證據](agent-ui-verification-evidence.md)。
- [x] Runs URL state 與 responsive summary grid 修改的前一版 image `sha256:a0d90694eb21f02b7b6a9d5f0870c0437bb1b668f19a46983fee968f3041f46d` 通過 Docker production build 與部署；Data Explorer 最新版另見下方驗收。
- [x] Data Explorer 最新 image 複驗：Memory、Learnings API 都回 200／0 筆並呈現成功空狀態；Knowledge config 回 404 但 Configuration／Content／Search 入口仍可切換，Content 與 Search 各呈現明確未配置錯誤及 Retry。375px 下 Search 查詢欄、型別與筆數控制垂直排列；`window.innerWidth` 與 document `scrollWidth` 都為 375，未發現水平溢位。Search 查詢字串未寫進 URL。
- [x] 401 恢復：第一次 Refresh 仍收到 401；依使用者先前明確授權，從本機 `pocs/agno/.env` 將目前 OS_SECURITY_KEY 重新送入遮罩欄位並儲存，資料庫選項與 Knowledge 請求恢復。未輸出、截圖或記錄 key 值。
- [x] 最新資料畫面存為 `screenshots/data-knowledge-config-unavailable-desktop.jpg`、`data-knowledge-content-unavailable-desktop.jpg`、`data-knowledge-search-unconfigured-desktop.jpg`、`data-knowledge-search-unconfigured-375px.jpg`；Memory／Learning 最新 375px 截圖為 `data-memory-empty-375px-latest.jpg`、`data-learnings-empty-375px-latest.jpg`。錄影 API 不可用，沿用截圖留證。
- [x] P2.2 開工前 Trace／Metrics 契約盤點：AgentOS 2.9.0 `/traces` 為分頁 TraceSummary；`/traces/{trace_id}` 為 TraceDetail／TraceNode 階層；`/trace_session_stats` 提供 session trace 數及首末時間；`/metrics` 提供 DailyAggregatedMetrics、token 與 model metrics。
- [x] 以 AgentOS 容器既有 key 做唯讀 API 基線，僅輸出 status、筆數與 schema 欄位：選定 DB `/traces` 200／0、`/trace_session_stats` 200／0；2026-11-15～21 `/metrics` 200／2 筆。此環境沒有 Trace 可以演示，不以其他 session 或 Langfuse request spans 代替。
- [x] P2.2 source slice：新增 `ObservabilityExplorer.tsx`，以 AgentOS native Trace summary/detail tree 呈現、支援 run/session/status 篩選、分頁、Trace ID URL 深連結、selected DB、獨立 API loading/error/Retry；Metrics 頁支援日期區間、每日 Agent／Team／Workflow runs、sessions、token metrics、model metrics disclosure。資料不存在時呈現成功空結果，不用其他 trace 替代；成本不推算。
- [x] P2.2 Docker production build／部署及桌面／375px 瀏覽器驗收完成；Trace 0 rows、Metrics 2 rows、未知 Trace 404／Retry 與 Metrics 深連結都已驗並存圖。最新 build／部署 ID 與本次新增的 Run→Trace 導覽驗收，記在本文件末尾的 2026-11-21 最新 checkpoint。
- [ ] 待續：以有紀錄的 Memory／Learning 與已配置 Knowledge instance 驗欄位、分頁及內容來源；Runs 斷線復原與真實 run→trace 正向關聯（Run→Traces 導覽已完成）；Factory/runtime 404 局部降級與 Retry、endpoint 切換的 token／快取隔離、125% zoom、鍵盤 focus／Esc、API contract 對照及 F01–F17 其餘功能。
- [x] Runs URL state source：側欄 view 寫入 `view`；Runs 的 type/component/page/session/run 由各自 query state 驅動。使用者切換 type/component/DB/page/session/run 時同步更新並清除失效下游選取；`agent`／`team`／`session` 舊 Chat query 保留。
- [x] Docker image `sha256:03c71ee4305b29d94357a460a3278590edab90abbd4c28602688c8dde4f561e6` 部署後已用 375px 瀏覽器驗證：Agent 7 筆 sessions、首筆 session/run 自動選取；URL 同時保留舊 `agent` 與 `db_id`，並新增 `view`、`session_type`、`component_id`、`session_id`、`run_id`。重載後重新授權，Runs 與同一 session/run detail 恢復。
- [x] Agent Runs 點選第 2 頁後，URL 增加 `runs_page=2` 並記錄頁面上選取的 session/run；重載、重新授權後仍回到第 2 頁的同一 session/run detail。網址原有 Chat `agent` 和 DB `db_id` 皆保留。
- [x] 過期 `session_id` 不會被自動覆蓋；Sessions 清單保留且提示該 session 不在目前 DB／頁面。過期 `run_id` 顯示 AgentOS `404 Not Found` 與 Retry；清除錯誤 ID 後重新開啟原有效網址已恢復 `COMPLETED` run、6 messages、2 tool calls。
- [x] 瀏覽器截圖發現 1280px 詳情欄 4 張 summary 卡太窄，`Not returned` 垂直折行。已將 summary grid 改成 2 欄、2xl 才 4 欄；新 image build／部署後在 1280px 確認文字正常，在 375px 確認 Runs summary 及 Agent run data 可讀。
- [x] 最新 Docker UI image 重新載入後，重新授權 Token 可還原 Agent list、Session、Run 與 page 2。截圖：[375px Agent list](screenshots/runs-deep-link-agent-375px-after-fix.png)、[page 2 reload](screenshots/runs-deep-link-page-2-375px.png)、[desktop summary](screenshots/runs-deep-link-agent-desktop.png)、[375px run data](screenshots/runs-agent-data-375px.png)。
- [x] F11 native trace source check：Agno `/traces?run_id=...&db_id=...` 與同一 run 的 session query 均回 200／0 records；整個選定 DB `/traces?db_id=...` 也為 0。OpenAPI 確認 detail schema 可提供 `TraceDetail.tree`、span type/status/timing/input/output/error；此 DB 目前沒有資料可以展示。不可把 Langfuse HTTP request spans 或同 session 的其他 traces 冒充該 run 的 trace。
- [x] 下一切片 API contract check：選定 DB 的 `/memories` 與 `/learnings` 均回 200／0 items；`/knowledge/config?db_id=...` 回 404 `Knowledge instance ... not found`。OpenAPI 提供 Memory、Learning record 欄位和分頁參數。
- [x] Data Explorer 第一版已完成 Docker build 與瀏覽器驗收：新增 sidebar Data view、Memory／Learnings／Knowledge tabs、DB selector、URL state `view=data`／`data_type`／`data_page`／`db_id`。Memory／Learning 卡片依 OpenAPI 顯示白名單欄位及 full record disclosure；Knowledge 404 轉成明確的未配置狀態。375px 與桌面畫面已截圖。
- [x] Data Explorer 首次 Docker build 在 Next compile 失敗：新建未追蹤的 `DataExplorer.tsx` 沒被 `git diff` 收入 POC patch，容器因此找不到模組。需用 intent-to-add 納入 patch 後重建；不是程式 import 路徑錯誤。
- [x] 將 `DataExplorer.tsx` 以 intent-to-add 納入 patch 後，第二次 production build 通過 patch apply、522 套件 frozen install、Next compile、lint、TypeScript、static generation；image `sha256:030c154bfabb79172395197cdad3e0398cde9b940600e5212d7f6495215ca3cc`。Compose 部署與 UI 瀏覽器驗收完成，UI image ID `030c154bfabb`。
- [x] Docker UI 在 375px 實測 Memory 與 Learnings 請求成功但各為 0 items，明確顯示成功空狀態；Knowledge config 回 404 時顯示「No Knowledge instance is configured for this database.」而非空知識庫。375px 與 1280px 畫面見[驗收證據](agent-ui-verification-evidence.md)。
- [x] Data URL 深連結含 `view=data`、`data_type=knowledge`、`db_id`；重載並重新授權後還原 Data view、Knowledge 分頁與所選 DB。Token 只在 UI 記憶體使用、畫面遮罩，未寫入文件或截圖。
- [x] 以本機 Docker AgentOS 2.9.0 `/openapi.json` 核對 Knowledge contract：`GET /knowledge/content` 回 paginated `ContentResponseSchema`，含 id/name/type/size/status/status_message/metadata/timestamps；`POST /knowledge/search` 是查詢 API，接受 query、db_id、knowledge_id、vector_db_ids、search_type、max_results 等；remote source listing 必須帶 knowledge_id。Data view 目前只讀 config，下一切片補 content list／search，不加入任何 upload/delete/update 操作。
- [x] Knowledge content list／readonly search 第一版 production build、部署至 image `sha256:67e3c69cd0bf8269f788d78952efdf1f84b8f6deebc02eceee885471c633940c` 完成；重新授權後確認本機 Knowledge config 真實回未配置 404。
- [x] 瀏覽器實測發現 config 404 會遮掉 Content／Search 子頁入口；已修改為保留子頁導覽，Configuration、Content、Search 各自呈現配置／API 狀態，不讓單一來源錯誤隱藏其他功能。新 image `sha256:e05479e55c3f173d60f7913e1b79d44245daa7fddc0a74f95a256e5d02c4a446` 通過 patch apply、522 套件 frozen install、Next compile、lint、TypeScript、static generation；Compose 部署與瀏覽器驗收待完成。
- [x] Knowledge content/search 首次 production build 在 TypeScript 檢查失敗：OpenAPI payload 中 description/status_message 為 `unknown`，JSX 條件式不能直接渲染。已改為先檢查 string 型別及非空，再重新 build；失敗 image 未部署。
- [x] 依使用者要求清理我在 2026-11-21 為 `agno-factory-local` 建立的舊 Docker image：12 個已被新版取代的 Agent UI image，以及 1 個 AgentOS 重建前 image。所有候選都以 Compose project/service label 確認歸屬、確認 dangling 並確認無 running/stopped container 引用後才逐一刪除。保留目前運行的 `030c154...`、11/14 基準版、Agno Tempo 與其他專案 images；未執行 prune，未動 build cache／volume／container。Docker image virtual size 不等於實際可回收磁碟空間；`docker system df` 顯示全域仍有 28.6GB 可回收項目，但不屬於本次授權範圍。

## 前一階段接手點（2026-11-21；歷史記錄）

本節以下是本輪開始時的歷史 checkpoint，後續新驗收結果請以文件末端的「窄版 UI 與 Agent 資訊驗收 checkpoint」為準。

- [x] 使用者在 Agent UI 重載後重新輸入 Token。頁面只以遮罩顯示；未從瀏覽器讀取或輸出 Token。使用者已明確授權：如後續需要，可從本機 `pocs/agno/.env` 複製 OS_SECURITY_KEY 到本機 Agent UI；不得輸出到聊天或文件。
- [x] Docker UI 容器 `factory-agent-ui` 已由最新 patch 重建，image 為 `sha256:56dae191d801080ae522ca15776c4b3205091eebda401f4272942f900a0e2f70`。本次 `docker compose ... ps --all` 顯示 Agent UI 與 AgentOS Up、Agno DB healthy；`http://127.0.0.1:3000` 實際載入新版 UI。
- [x] 新版瀏覽器載入看到兩個 Workflow；Software Delivery 顯示 22 steps、11 agents、1 team 及 revision `bdcc8db58b2161b3`。Agents 頁顯示 26 agents／3 teams。已查看 Testing Agent 的 role、summary、inputs/outputs、skills、完整 instructions、model 與 4 個 runtime tools，以及 Observability Team 的 instructions、mode、模型、delegate tool 和 4 個 members。
- [x] 已展開並檢視 Agent／Team 的 `Full Factory definition` 與 `Full AgentOS runtime response`。Knowledge 與 Memory 在該 AgentOS component detail API 沒有回傳，UI 明確呈現資料不可用；檢視過的兩種 payload 沒有出現 api_key、secret、password、token、credential、authorization 欄名。
- [x] 已在 `agent-ui-delivery/src/components/chat/Sidebar/Sidebar.tsx` 加上窄版側欄自動收合、保留 Chat／Workflows／Agents 圖示導覽的修正，重新產生 `pocs/agno/agent-ui.patch`，再以 Docker production build 驗證並重載。
- [x] 已執行 `docker compose -f pocs/agno/docker-compose.yml build agent-ui`；Docker build 通過 `git apply --check`、frozen install（522 packages）、Next production compile、lint、TypeScript 與靜態頁面產生。新 image 為 `sha256:199fafdd7dc44425afc2e8350f0a3f6a338c508c6dbf42f2080fd73ced94f85d`。
- [x] 執行 `docker compose -f pocs/agno/docker-compose.yml up -d --wait agent-ui` 後，`factory-agent-ui` 重建並啟動；該次輸出確認 AgentOS 與 Agno DB 啟動。最終 `docker compose ... ps --all` 顯示 UI／AgentOS Up、Agno DB healthy。
- [x] F07 Sessions error-state slice 已納入 `pocs/agno/agent-ui.patch` 並完成 Docker production build。image `sha256:56dae191d801080ae522ca15776c4b3205091eebda401f4272942f900a0e2f70` 已啟動，使用者重載並重新輸入 Token 後確認新版 Workflow 頁可載入。
- [x] 新版 Chat 側欄讀取到 7 筆既有 Agent Sessions；畫面證據為 [chat-sessions-375px-before-fix.jpg](screenshots/chat-sessions-375px-before-fix.jpg)。
- [ ] 375px Chat 歡迎頁仍有水平裁切：收合側欄後，welcome heading/content 仍超出可見畫面。要修正 ChatBlankState/ChatArea 的 shrink/wrapping，並用同一 viewport 重驗。
- [ ] 為測 401 點擊 UI 的 Clear token 後，Agents/Teams 請求顯示 Unauthorized，Sessions 區卻回到 `No Session found`，沒有 Retry。AgentOS log 沒有 Sessions access-log 命中（服務不一定有 access logging，故不能據此斷定沒送請求）。目前還不能宣稱 Sessions 401/Retry 已驗；需確認沒有選到 agent 時不會發生假空狀態，並以可重現的 Sessions API failure 再測。
- [x] Reload 後 `NO TOKEN SET`、手動重新輸入與 masked token 行為已先前驗過；本次 401 測試按 Clear token 後頁面回到 `NO TOKEN SET`。使用者已授權從本機 `.env` 取用 key；後續 F03／F04／F05／F07／F16 browser 驗收與 production proxy 邊界已記於本文件最上方。
- [x] Workflow 在 590／470／375px viewport 驗收。文件與主內容區寬度相等、沒有頁面水平溢位；主內容寬分別為 538／418／323px，側欄收合成 40px 圖示列。Agent/Team 頁也在 375px 檢查。
- [x] 螢幕證據已整理於 [agent-ui-verification-evidence.md](agent-ui-verification-evidence.md) 並嵌入截圖。瀏覽器沒有錄影能力，此次交付以截圖記錄。
- [x] 驗收後保留瀏覽器於 Workflow → Software Delivery，畫面顯示 22 steps／11 agents／1 team，Token 仍為遮罩。瀏覽器目前保留在 375px viewport 測試尺寸；下次接手若要一般桌面寬度，先清除 viewport override，再於不重載頁面的前提下確認 UI。
- [ ] 剩餘：用故障注入驗收 Factory/runtime 404 降級與重試；補 125% 縮放和鍵盤 focus/Esc 驗收；續做 OpenAPI 功能家族盤點及 F07–F17。

### F07 Sessions/Runs 後續切片（進行中）

- [x] 切片 1 程式修改：Chat 側欄 Sessions API 不再把 404 和網路／其他 HTTP 錯誤轉成 `{ data: [] }`；狀態錯誤傳到現有 Sessions 面板，空結果仍保留原本的 empty state，錯誤則顯示訊息與 Retry。未改聊天訊息解析或 session 刪除行為。
- 修改檔案：`agent-ui-delivery/src/api/os.ts`、`src/store.ts`、`src/hooks/useSessionLoader.tsx`、`src/components/chat/Sidebar/Sessions/Sessions.tsx`、`SessionBlankState.tsx`；差異已重新產生至 `pocs/agno/agent-ui.patch`。
- [x] Docker production build 通過 patch apply check、522 套件 frozen install、Next compile、lint、TypeScript 與靜態頁產生；image 為 `sha256:56dae191d801080ae522ca15776c4b3205091eebda401f4272942f900a0e2f70`。`up -d --wait agent-ui` 已完成，該次輸出 UI、AgentOS、Agno DB 均 healthy。
- [x] 新版 bundle 正常 Sessions 成功情境在瀏覽器載入 7 筆既有紀錄；截圖在 `screenshots/chat-sessions-375px-before-fix.jpg`。
- [x] Sessions 401／Retry 已由本機瀏覽器驗收，畫面顯示 `AgentOS returned 401 Unauthorized`；截圖為 [sessions-401-retry-drawer-375px.jpg](screenshots/sessions-401-retry-drawer-375px.jpg)。授權 Token 恢復後載入 7 筆 Sessions。
- [x] Chat 窄版修正已重新產生至 POC patch 並在新版 Docker UI 驗收；Chat welcome、側欄浮層與 Workflow Agent 卡片截圖連結見最新接手點及驗收證據文件。
- [ ] 後續切片：AgentOS workflow sessions/runs 類型、分頁與 detail；需按 2.9.0 API 契約增補，不把 Workflow 執行誤作 Agent Chat。

### Chat 窄版歡迎頁修正（進行中）

- [x] 於約 368px 瀏覽器 viewport 重現 Chat welcome 橫向溢位；截圖 [chat-sessions-375px-before-fix.jpg](screenshots/chat-sessions-375px-before-fix.jpg) 同時記錄 Sessions 已成功顯示 7 筆資料及頁面超寬現象。
- 原因：`ChatBlankState` 的標題 row 強制 `whitespace-nowrap`，Chat flex 主欄與訊息容器缺 `min-w-0`。已修改 `ChatArea.tsx`、`MessageArea.tsx`、`ChatBlankState.tsx` 以支援主欄收縮、標題折行及按鈕換行。
- [x] Patch 已重新產生，Docker production image `sha256:ea5cdf26e50e1866954bc4560da376754592e36378ac5dc01faebabe61cadcfb` 已啟動並於 375px 瀏覽器驗收。側欄展開已改為 overlay drawer，Chat welcome 與輸入框均在畫面內；Token 依授權從本機 `.env` 讀取後僅以遮罩顯示。

## 2026-11-21 起跑基線

- [x] Compose project 是 `agno-factory-local`；服務名稱含 `agent-ui`、`agentos`、`agno-db`、`langfuse-web`、`langfuse-worker`、`agno-gateway`。
- [x] Compose 設定把 Agent UI、AgentOS、Langfuse 對應至宿主機 3000、7777、3001。`docker compose ... ps -a` 顯示長駐服務在開始此輪時都已停止；因此尚未證明瀏覽器 UI 可用。
- [x] 舊本機 image `agno-factory-local-agentos:latest` ID 為 `sha256:c61a4438bd452a801e24bf128287c76346832ad7b273694d92b3a97c31a9dd87`，內含 Agno 2.9.0，但未安裝 Langfuse Python 套件。這是舊 image，不代表目前修改的 requirements 已建置。
- [x] 舊 UI image ID 為 `sha256:218f72597b913e47471cd69efb3e1d37e261f34d9ddec3b54ea97d964564c7e3`，內含上游 commit `6dad9593fca6756e1813e4f4b3b2620be6377691`。
- [x] 目前 registry snapshot 為 `bdcc8db58b2161b1`，包含 26 agents、3 teams、2 workflows。以 Compose run 執行 `integration.registry.load()` 取得，沒有啟動 API 或呼叫模型。
- [x] 影音工具盤點：目前可用的瀏覽器操作工具有單張／整頁截圖介面，沒有可輸出瀏覽器操作影片的錄影方法。此輪使用截圖並直接嵌入文件。

## 執行進度

- [x] 記錄 Docker、UI commit、Agno 版本和 registry revision。
- [x] P0.2 UI：`pocs/agno/Dockerfile.ui` 固定 fork commit `817a009b3d7e407b17b48872f5bbf1c5055b5955`。Docker build 成功從 fork 抓取該 commit、通過 patch `git apply --check`、以 frozen lockfile 安裝 522 個套件，Next.js production build、lint 與型別檢查成功。Agent/Team raw-detail 調整後最新 UI image `sha256:3471401b8522922025350a69c58df7c42ffa8c1ce9aa2cee34520cdb76fd49bf`。
- [ ] P0.4（部分驗收）：已移除 `NEXT_PUBLIC_OS_SECURITY_KEY` 注入；隔離掃描 image 靜態檔未發現 `.env` OS key，process environment 也未設定該公開變數。無 Token 的 UI API 401、使用者手動輸入後成功載入資料，以及重載後回到 `NO TOKEN SET` 均已驗。最新 image `bab1260…` 已用 synthetic state 驗 endpoint 切換會清 Token／快取／URL；真實 stream abort 後無 stale callback 尚待驗。
- [x] P0.5：已在 `pocs/agno/app.py` 加入 Agent／Team／Workflow 三個 Factory 詳情路由，回應限定白名單欄位並沿用 AgentOS 認證。Docker HTTP 驗證：無 Token 401；revision、已知 Agent/Team/Workflow 200；未知 Workflow 404；三類資料 revision 相符；回應未包含 `/app/`、Windows 絕對路徑或憑證標記。
- [x] P1.2 驗收故事：新版 UI 已載入 Workflows／Agents／Teams；Software Delivery 的 Parallel Verification 分支和 Testing Agent 詳情、Continuous Improvement 的 Observability Team 及成員導覽已驗，詳見證據文件。
- [x] P1.1 部分來源故障／重試：2026-11-22 以本機合成 fixture 分別驗 Factory definition 404 與 runtime detail 404；錯誤文案／Retry 可見，且 Retry 僅重送失敗來源，成功來源保留。

### 本次修改檔案

- `pocs/agno/Dockerfile.ui`：固定 fork commit，套用 POC patch，凍結套件安裝；已移除公開 Token 的 build arg。
- `pocs/agno/docker-compose.yml`：移除 Agent UI build/runtime 的 `NEXT_PUBLIC_OS_SECURITY_KEY`。
- `pocs/agno/agent-ui.patch`：修改自固定 fork commit，包含 auth token 由使用者即時輸入的前端修改。`authToken` 不在 Zustand persist 的 `partialize` 欄位內。
- `pocs/agno/agent-ui.patch`：加入 Workflow runtime-first 讀取；Factory revision 與設計 API 分開失敗處理，Factory 詳情不可用時仍保留原生 AgentOS 步驟樹並標示資料來源。
- `pocs/agno/agent-ui.patch`：Agent/Team 詳情新增「Full Factory definition」與「Full AgentOS runtime response」摺疊 JSON 區塊，顯示尚未被排版的原生欄位，如 tools config、system message、Team mode/members。檢查目前 Agno 2.9.0 回應的欄位名稱未發現 api_key/secret/password/token/credential。
- `pocs/agno/app.py`：加入三個 Factory 詳情路由，從程序啟動時已載入的 registry snapshot 選取欄位並共用 revision。
- `pocs/agno/README.md`：更新 Agent UI token 的 POC 說明。
- `pocs/agno/requirements.txt`：將 `agno[os]` 固定為 `2.9.0`，對齊本機已驗證 API 契約。
- `pocs/agno/requirements.lock`：新增完整 76 個 Python 套件版本鎖，Docker AgentOS 只依鎖檔安裝。
- `pocs/agno/Dockerfile.agentos`：安裝鎖定的 Python 套件集合。
- `agent-ui-delivery/` 是產生 `pocs/agno/agent-ui.patch` 的 fork checkout，裡面的未追蹤修改不是交付來源；後續請修改 POC patch 並從固定 commit 重建。

### UI Docker build（2026-11-21）

- [x] Docker 已取回 `CletusLee/agent-ui` commit `817a009b3d7e407b17b48872f5bbf1c5055b5955`。
- [x] `git apply --check /tmp/agent-ui.patch` 通過。
- [x] `pnpm install --frozen-lockfile` 成功，lockfile resolution skipped，522 個套件完成安裝。
- [x] `pnpm build` 編譯成功，Next lint 與型別檢查通過，靜態頁面產生成功。
- [x] 在無網路的臨時 UI container 以 `/tmp/agentos.env` 讀取本機 `.env`，只輸出布林結果。`publicKeyEnvDefined=false`、`securityKeyInStaticAssets=false`，掃描 25 個 build assets；沒有顯示 key 值。
- [x] 固定 UI patch 後第二次 Docker build 成功：`pnpm install --frozen-lockfile` 解析 522 個套件；Next.js production build 的編譯、lint、TypeScript 型別檢查與靜態頁面產生通過。新 image `sha256:df610c5e02e2c8844c5bc6ce7a045094f5f5c29545e14211c813a3a2234473f2`。
- [x] Agent/Team raw-detail UI 調整後 production build 成功，編譯、lint、TypeScript 型別檢查與靜態頁面產生通過；sidebar auto-collapse 修正後再次 production build 成功，最新 image `sha256:199fafdd7dc44425afc2e8350f0a3f6a338c508c6dbf42f2080fd73ced94f85d`，已透過 `up -d --wait agent-ui` 重啟。
- [x] 最新 image 再掃描靜態 JS/CSS/HTML，與本機 `.env` key 比對但不輸出 key：`keyConfigured=true`、`publicKeyEnvDefined=false`、`securityKeyInStaticAssets=false`、掃描 18 個 assets。
- [x] 針對最新 image 再掃描靜態 JS/CSS/HTML，與本機 `.env` key 比對但不輸出 key：`keyConfigured=true`、`publicKeyEnvDefined=false`、`securityKeyInStaticAssets=false`、掃描 18 個 assets。
- [x] 用 `docker compose ... up -d --wait agent-ui` 重建新版 UI container；AgentOS 與 Agno DB 也維持 healthy，Langfuse web/worker 與基礎依賴 healthy。
- [x] Windows sandbox 的 fork checkout `pnpm run validate` 因 pnpm 無法建立 store symlink（EPERM）而停止；未改動 pnpm store。Docker production build 內的 lint/typecheck 通過，作為本次程式檢查。
- [x] 最新 image 已啟動；已在瀏覽器載入 Agent/Team/Workflow 詳情並驗收詳情面板。最新 Docker 狀態於本次續作最後再確認。

### AgentOS 可重現建置（進行中）

- [x] 依起跑時實際使用的 Agno 2.9.0 固定 `agno[os]==2.9.0`，避免浮動至尚未驗證的版本。
- [x] 從直接依賴清單產生完整 Python 依賴 lock（76 套件），並讓 Docker image 只依 lock 安裝；鎖檔建置成功。
- [x] AgentOS image `sha256:05ab1a37ffe66455078e7bba1b16112a7e8bd4dc44874550c267fff828308f44` 啟動成功；容器回報 Agno 2.9.0。
- [x] 啟動後驗證 no-token 401、有效 token 讀取 revision／Agent／Team／Workflow 詳情、未知 ID 404，以及回應沒有內部檔案路徑或憑證。結果：401/200/200/200/200/404；revision 相同；資料量 26 agents、3 teams、2 workflows。
- [x] 一併啟動 POC Langfuse web/worker 與 Redis、ClickHouse、Postgres、MinIO 依賴，消除 AgentOS tracing 對未啟動 Langfuse 的重試。

### Workflow 降級顯示修正（2026-11-21）

- [x] 在 AgentOS 2.9.0 live API 確認 `/workflows` 回 2 筆；`/workflows/software-delivery` 回傳原生 `steps`；巢狀節點為 `Step`、`Condition`、`Parallel`，Agent/Team 以巢狀物件提供穩定 ID。
- [x] 在前端新增原生 Workflow detail API 與已知節點正規化；未知的原生葉節點顯示為 `AgentOS step`，不猜測或虛構 Python 函式名稱。
- [x] Workflow 清單和 Factory revision 改獨立處理；詳情先顯示原生 workflow，再用 Factory registry 資訊補上角色和版本。Factory 詳情 404 時仍保留原生設計。
- [ ] 尚未在瀏覽器以故障注入實際驗收 Factory 404、runtime 404 的畫面。

### AgentOS API 契約盤點（進行中）

- [x] 從執行中 AgentOS 的 OpenAPI 擷取去識別 operation inventory：75 paths、112 HTTP operations，含 method/path/operationId/tags/parameters/request/response schema refs/OpenAPI security 宣告與初步功能家族歸屬。
- [x] 新增 [agentos-api-contract.md](agentos-api-contract.md) 作為後續 AI 的部署契約起點；只存路由中繼資料與唯讀驗收狀態，不存 Token、模型 prompts、完整 request/response 或敏感 payload。
- [ ] 依 OpenAPI parameters/response 完成分頁、DB、錯誤狀態及 F01～F17 的逐 operation 對照。只實測少量已核准的 GET；沒有把「有路由」誤記為「已配置」或「有資料」。

### 瀏覽器驗收（2026-11-21）

新版 Docker UI 的成功與錯誤狀態、Software Delivery 與 Continuous Improvement 兩條路徑、Agent／Team 詳情以及 590／470／375px 排版均完成驗收。詳見[逐項驗收與截圖](agent-ui-verification-evidence.md)。無 Token 401 及重載清除 Token 的證據仍保留：[no-token-workflow-401.jpg](screenshots/no-token-workflow-401.jpg)、[no-token-after-reload.jpg](screenshots/no-token-after-reload.jpg)。

### 待續項目

- Factory/runtime 404 故障注入與重試的瀏覽器呈現。
- endpoint 切換的 Token／快取隔離，以及該操作的請求記錄檢查。
- 125% 縮放、鍵盤 focus trap/Esc 回焦與其餘 P0.3、F07–F17 範圍。

## 2026-11-21 窄版側欄覆驗 checkpoint

- [x] 使用者已明確授權可自行從 `pocs/agno/.env` 讀取 `OS_SECURITY_KEY` 並填入本機 Agent UI。值只送入瀏覽器的密碼欄位，畫面僅顯示遮罩；未列印、未寫入文件或截圖。
- [x] Docker Compose 狀態確認：`factory-agent-ui`、`factory-agentos`、`factory-agno-db` 均在執行，資料庫 healthy；Langfuse 相關容器也在執行。
- [x] 最新部署頁重載後用本機 key 驗證：Workflow 定義 revision `bdcc8db58b2161b3` 成功載入；Software Delivery 顯示 22 steps、11 agents、1 team。375px 證據已保存為 `screenshots/workflow-software-delivery-375px-after-drawer-fix.jpg` 和 `screenshots/workflow-parallel-verification-375px-after-drawer-fix.jpg`。
- [x] 375px Chat welcome heading 可換行、輸入框留在主畫面內；Sessions 401／Retry 截圖已保存為 `screenshots/sessions-401-retry-drawer-375px.jpg`。
- [x] `Sidebar.tsx` 窄版浮層抽屜已重新產生 POC patch、Docker build／重啟並於瀏覽器實測；Workflow 主欄在抽屜打開時不被擠窄，背景遮罩可見。
- [x] Testing Agent 詳情及 AgentOS runtime JSON 在 375px 可讀；最新圖在 `screenshots/agent-testing-details-375px-after-drawer-fix.jpg`、`screenshots/agent-testing-runtime-375px-after-drawer-fix.jpg`。
- [ ] 下一步：Factory/runtime 404 局部降級與 Retry、endpoint 切換隔離、125% 縮放及鍵盤 focus/Esc、API contract 與 F07–F17。

## F07 Workflow Sessions／Runs API research（2026-11-21）

- [x] 直接從 Docker 中的 AgentOS 2.9.0 `openapi.json` 核對契約：`GET /sessions` 的 `type` 可為 `agent`／`team`／`workflow`，並支援 `component_id`、`limit`、`page`；回應為 `data` + `meta`。
- [x] 確認唯讀 run 路徑：`GET /sessions/{session_id}/runs?type=workflow&db_id=...` 回傳 `WorkflowRunSchema[]`；`GET /sessions/{session_id}/runs/{run_id}?type=workflow&db_id=...` 回傳單筆 run。Workflow run 包含 `status`、`step_results`、`step_executor_runs`、`events`、`metrics`、`run_input` 等欄位。
- [x] 本機資料基線：Software Delivery 查到 13 筆 Workflow sessions；`page=1&limit=5` 回傳 5 筆並有 pagination meta。抽樣一筆 session 的 Runs endpoint 回 200，含 1 筆 `COMPLETED` Workflow run。只記錄筆數、狀態和 schema 欄名，不保存 session/run ID 或工作內容。
- [x] 實作 UI slice：新增唯讀 Runs 工作區，以 Workflow 篩選、分頁瀏覽 Sessions，檢視 session 的 run 狀態與步驟結果；完整 API payload 收在可折疊 JSON 區。沒有建立／續跑／取消等寫入動作。
- [x] 以 Docker UI 驗 `GET /sessions`、`GET /sessions/{id}/runs`、`GET /sessions/{id}/runs/{run_id}` 的實際回應並更新驗收證據；375px 載入 13 筆 Software Delivery Workflow sessions、每頁 5 筆共 3 頁，成功切至第 2 頁；選取的 run 顯示 `COMPLETED`、2 step results、0 executor runs、0 events。畫面見 `screenshots/workflow-runs-list-software-delivery-375px.jpg` 與 `screenshots/workflow-run-details-software-delivery-375px.jpg`。

## F07 Runs Explorer implementation checkpoint（2026-11-21）

- [x] Fork source has a new read-only `RunExplorer`: workflow selection, paginated workflow-session list, selected session’s run list, selected run details, step result summaries and expandable full session/run JSON. No create/continue/cancel/delete actions.
- [x] API layer now supports workflow session filtering plus `page`/`limit`, and typed `GET /sessions/{session_id}/runs` and `GET /sessions/{session_id}/runs/{run_id}` helpers.
- [x] Sidebar and workspace routing now include a Workflow Runs view.
- [x] 把 `RunExplorer.tsx` 納入 `pocs/agno/agent-ui.patch` 後完成 Docker production build；Next compile、lint、TypeScript 與 static generation 通過，image ID 為 `sha256:3ee9544960a42bfd05c9fbbfad742b8c2af0d6e394e8dd959ac95b4d37f46d8f`。
- [x] 第一次 Workflow Runs Docker build 暴露 packaging 漏項：新建的 `RunExplorer.tsx` 尚未納入 fork 的 `git diff` patch，Next 因找不到 `@/components/runs/RunExplorer` 而停止；本次未進入 TypeScript 檢查，也未部署失敗 image。
- [x] 把新檔納入 patch 後重跑 build；`docker compose -f pocs/agno/docker-compose.yml up -d --wait agent-ui` 成功。以瀏覽器重載確認新 image、用本機 `.env` 的授權 Token 讀到真實 Workflow session/run，並保存 375px list/detail 截圖。截圖不含 Token；Token 沒有寫入文件。

### F07 下一切片

- [x] 用本機 AgentOS 的授權唯讀 GET 核對 `type=agent`／`component_id=sdlc-ticket-agent` 有 7 筆 sessions、`type=team`／`component_id=observability-team` 有 1 筆；兩類 `/sessions/{id}/runs` 與 `/runs/{run_id}` 都回 200。抽樣 Agent run 回 1／3 筆、Team run 回 5 筆，detail 狀態均為 `COMPLETED`。Agent／Team payload 有 messages、tools、events、metrics 等欄位，不含 Workflow `step_results`；不保存 ID 或內容。
- [x] Runs Explorer source 已擴充 Agent／Team／Workflow 三種原生 session type。共用原始 run record 顯示通用欄位，Workflow 專屬 step results 條件呈現；不把 Agent／Team run 強制轉型成 Workflow run。
- [x] 元件清單隨 session type 變化，session detail 顯示元件名稱、ID 與目前 DB scope；載入／空資料／HTTP error／網路 error 使用獨立狀態呈現。既有 Workflow 13 sessions／3 頁回歸能力保留。
- [x] 更新後 Docker production build 通過 patch apply、522 套件 frozen install、Next production compilation、lint 與 TypeScript；image `sha256:1787b49a22f11a19178afd4cae52d741073906ea491300f2aa4753e5fdeaef85` 已建立。
- [x] 最新 Docker image `sha256:1787b49a22f11a19178afd4cae52d741073906ea491300f2aa4753e5fdeaef85` 已部署；375px 實際驗 Agent／Team／Workflow 三類 session 與 Runs。Agent：7 sessions、抽樣 run `COMPLETED`，6 messages／2 tool calls；Team：Observability 1 session／5 `COMPLETED` runs，抽樣 run 有 3 messages；Workflow：Software Delivery 13 sessions、5 筆／頁共 3 頁，抽樣 run `COMPLETED` 且有 2 step results。截圖列於[驗收證據](agent-ui-verification-evidence.md)。
- [x] 驗到成功但空的 200 狀態：Governance Team `0 sessions` 顯示明確空狀態，沒有偽裝成 API error；無 Token 時 component API 顯示 `AgentOS returned 401 Unauthorized` 與 Retry。從 `.env` 讀取授權 Token 後已恢復並顯示遮罩。
- [x] DB 選取與 desktop Runs 視覺已驗；`db_id` 在 reload 保留，但目前只測此 query 欄位，type/component/session/run 深連結及選取還原尚未實作／驗收。
- [ ] 404／斷線故障與真實 run→trace 正向關聯仍待處理；從 Workflow Run 導航至精確 Trace run filter 已驗，詳見本文件末尾最新 checkpoint。

## F07 Agent／Team run contract checkpoint（2026-11-21）

- [x] AgentOS 2.9.0 唯讀基線已由 Docker 內既有 `OS_SECURITY_KEY` 查詢：Agent `sdlc-ticket-agent` 有 7 筆 session，Team `observability-team` 有 1 筆；兩類 runs list 與 run detail 都回 200。抽樣 Agent session 有 1、3 筆 runs，Team session 有 5 筆，抽樣 detail 均為 `COMPLETED`。
- [x] 確認 Agent／Team run payload 可讀欄位包含 `messages`、`tools`、`events`、`metrics`、`run_input`、`content`，而 Workflow 的 `step_results` 為專屬欄位；只記欄名、數量和狀態，不保存 ID 或工作內容。
- [x] Fork source 已開始擴充共用 Runs Explorer：三種 session type、依類型載入元件、沿用 `/sessions` 分頁與 DB query、將 run type 明確帶入 runs/detail API，並將 Agent／Team message/tool/event 資料與 Workflow step results 分別呈現。
- [x] POC patch 已重新生成，Docker build、部署及瀏覽器驗收完成；三種 session type 和各自的 run detail、空狀態與 401／Retry 截圖都更新到能力計畫與驗收證據。

## P2.2 Observability 瀏覽器驗收 checkpoint（2026-11-21）

- [x] 已確認 Compose 重建的 `factory-agent-ui` 使用 image `sha256:c731f175e1d1ca7779f8c686a621c3cbb468ce5da82ab72a3ec0cef58bf049ac`；瀏覽器重新載入後側欄有 `Observe`，Observability workspace 可開啟。AgentOS 與 Agno DB 維持執行，DB healthy。
- [x] 使用者已授權可從 POC `.env` 複製本機 `OS_SECURITY_KEY`。只將 key 填入本機頁面的遮罩欄位；沒有列印或保存到文件／截圖。重載後 Token 回到 `NO TOKEN SET`，重新填入後 Metrics 與 Traces 可讀。
- [x] 桌面頁面驗證：`GET /traces` 與 `GET /trace_session_stats` 成功但各有 0 筆；UI 明確說明目前 DB 沒有 Trace。`GET /metrics` 的日期範圍為 2026-11-15 至 2026-11-21，回 2 日資料列，合計 35 runs、31 sessions、989,821 API-reported tokens；成本欄位標示未提供且不估算。
- [x] 375px 實際瀏覽器 viewport 驗證 Metrics 與 Traces：兩頁的 `window.innerWidth`／document scroll width 均為 375px，沒有水平溢位；手機版表單和摘要卡改為直向排列。截圖：[Metrics desktop](screenshots/observability-metrics-desktop.jpg)、[Metrics 375px](screenshots/observability-metrics-375px.jpg)、[Traces empty desktop](screenshots/observability-traces-empty-desktop.jpg)、[Traces empty 375px](screenshots/observability-traces-empty-375px.jpg)。
- [x] 以不存在的 `trace_id` 開啟深連結，Trace detail 區顯示 not-found 與 Retry，沒有用 0 筆清單假裝查到 detail。截圖：[Trace not found](screenshots/observability-trace-not-found-desktop.jpg)。此驗收用合成不存在 ID，只測錯誤狀態；未保存 trace ID 或真實內容。
- [x] 已從 AgentOS 2.9.0 實際 router 核對 `/metrics` 的 `table` 為可選字串；`get_db(dbs, db_id, table)` 在指定 table 時會確認該 table 已在該 DB 設定且存在，且 table 有值時 `db_id` 必填。
- [x] 依 AgentOS 2.9.0 router contract，在 fork source 新增 optional table 欄位、`metrics_table` URL state 和 GET query 傳遞；留白不傳 query，沿用 DB 預設。table 有值但 URL 無 `db_id` 時，UI 顯示選擇具名 DB 的說明並停止 request；這段 source 已包含在本文件後續記錄的 Docker image `25d2e4b...`。
- [x] 為避免使用者只能從別的頁面改 DB，Observability source 新增 Database selector，沿用 `getSessionDatabaseOptionsAPI`，URL 保留 `db_id`；切換範圍時清除 trace detail、page 與 table name。table input 同步 `metrics_table` query state。
- [x] 此 checkpoint 的 patch／build／部署、DB selector、`agno_metrics` table filter、URL reload 與 default DB 下 table precondition 已完成並有證據，最終 image 及 Compose 狀態見下方最新 checkpoint。無效／不存在 table 名稱的 AgentOS 錯誤狀態尚未從瀏覽器驗收。
- [ ] 真實資料庫目前沒有 native traces；仍待有真實 Trace 後驗 span tree、input/output、metadata、trace/run 精確關聯，以及此 AgentOS 版本的正向 detail schema。

## P2.2 DB／Metrics table 驗收與 Run→Trace gap checkpoint（2026-11-21）

- [x] 最新先行部署 image 為 `sha256:3c211d378f1032cd8fad5a9fc4ef241614035c250ccfb025bcb730e3115d9ec6`。Docker production build 的 patch apply、Next compile、lint、TypeScript、static generation 通過；`docker compose ... up -d --wait agent-ui` 後 UI、AgentOS、Agno DB 均 healthy。
- [x] 已確認目前 PostgreSQL 實際設定的 Metrics table 名稱為 `agno_metrics`；直接向 AgentOS 送出唯讀 `/metrics` request，`db_id + table=agno_metrics + 2026-11-15..2026-11-21` 回 200、2 rows、35 runs、31 sessions。容器 key 只作 Authorization header，未輸出值。
- [x] 實際操作 DB selector：`AgentOS default` 與具名 DB 選項載入；切到 default 會移除 `db_id` 並重設 table；有 table 卻未選具名 DB 時 UI 顯示 `Select a specific database before choosing a table.`，不送出 API request；選回具名 DB 後 `agno_metrics` 正常回傳。
- [x] 輸入 `agno_metrics` 並 Apply 後，URL 帶 `metrics_table=agno_metrics`；瀏覽器 reload／重新輸入本機 Token 後 DB、日期和 table 值還原，Metrics 仍有 2 rows。桌面與 375px 截圖已更新到[驗收證據](agent-ui-verification-evidence.md)；375px document 寬度 375，沒有水平溢位。
- [x] Fork source 在 selected run detail 加入 `View traces for this run`；同頁切換 Observability，設定 `view=observability`、`observability_view=traces`、精確 `trace_run_id` 與 page 1，保留 DB，清掉舊 trace session/status/detail filter。尚未建置。
- [x] 重產含 Run→Trace 導覽的 `pocs/agno/agent-ui.patch`，Docker production build／deploy；從真實 Workflow run 點擊並確認 workspace、`trace_run_id`、`db_id` 與成功空結果，已更新截圖。真實 Trace detail/span tree 仍待 native Trace fixture。
- [x] F16 System Explorer 已完成 Docker 部署及 Desktop 驗收；AgentOS health、版本、註冊元件、DB、model、interfaces/MCP 與 Factory revision 各按其來源呈現；未檢查的外部整合以中性 `Not checked` 標記。實際數字見本文件底部 F16 checkpoint。Token 輸入框遮罩，截圖未含原值。

## P2.2 最終部署與 Run→Trace 驗收 checkpoint（2026-11-21）

- [x] Docker production build 以目前 `pocs/agno/agent-ui.patch` 成功完成；Fork source commit 為 `817a009b3d7e407b17b48872f5bbf1c5055b5955`。Next production compilation、lint、TypeScript 與 static generation 通過。最終 image：`sha256:25d2e4b15ecc58f6c682bf95b7bba21a1e656771b8dfcd29f625aa292c8a38e9`。
- [x] `docker compose -f pocs/agno/docker-compose.yml up -d --wait agent-ui` 已部署；Docker inspect 確認 `factory-agent-ui` running 且 image 正確；Compose 狀態為 `factory-agentos` running、`factory-agno-db` healthy，Langfuse web／worker 及依賴也 running／healthy。沒有清理 Docker images、volumes 或其他容器。
- [x] 本機瀏覽器已用使用者預先輸入的 key 正常呼叫 AgentOS；UI 欄位保持遮罩。Metrics 的選定 DB、日期 `2026-11-15..2026-11-21` 與 `agno_metrics` table 顯示 2 日資料、35 runs、31 sessions、989,821 token；成本明確標示 API 未提供。表格及 run filter 證據：[Metrics table](screenshots/observability-metrics-table-filter-desktop.jpg)。
- [x] 從實際 Workflow run detail 點擊 `View traces for this run`，實際跳到 Observability／Traces，帶入相同 DB 和該 run 的精確 `trace_run_id`；清除舊 trace-specific filters。AgentOS 回成功空結果（0 traces／0 sessions with traces），UI 沒有以 Workflow steps 或外部 span 假造 trace。證據：[Run detail action](screenshots/workflow-run-traces-link.jpg)、[Run-filtered Trace result](screenshots/observability-run-trace-filter-empty-desktop.jpg)。
- [x] 畫面目視檢查完成：Workflow run detail 的「View traces」按鈕、所選 Run ID、6 個 step results／10 executor runs，以及 Trace 頁 Run ID filter、具名 DB、成功空結果皆可讀。375px Metrics／Traces 的 document width 等於 viewport 375px；證據見 `observability-metrics-375px.jpg`、`observability-traces-empty-375px.jpg`。
- [ ] 目前 Agno DB 沒有 native traces；無法驗真實 `/traces/{trace_id}` detail、span hierarchy／input-output 與正向 run-to-trace 關聯。要等此 DB 有可用原生 Trace fixture 後再勾選；不得以合成 span 取代。
- [ ] 下一步：驗證輸入不存在的 Metrics table 時 AgentOS error／Retry 顯示；取得 native Trace fixture 後驗 detail/span tree。接著完成 OpenAPI 75 paths／112 operations 與 F01–F17 逐項 endpoint/權限/資料狀態對照；續做 F06、F13–F17 唯讀覆蓋、斷線恢復／endpoint 隔離與 125%／鍵盤無障礙驗收。不要重建本次已部署 image，除非 source／patch 有改動。

## F16 System Explorer Docker／Desktop 驗收 checkpoint（2026-11-21，Agno 2.9.0 歷史記錄）

- [x] 直接查詢本機 AgentOS 2.9.0 唯讀 `/health`、`/info`、`/config`、`/models`，只記可公開摘要：各 endpoint 回 200；健康 status／初始化時間、Agno version 2.9.0、OS ID、auth mode、元件數與 MCP enabled 可從 `/health`／`/info` 讀到；`/config` 有 26 agents、3 teams、2 workflows、1 個 session DB、0 interfaces；`/models` 回 1 筆 model。沒有保存原始 config 或 credentials。
- [x] fork source 新增白名單 System API projection：`/config` 只回 component id/name/description、session `db_id`、interface id/name/type；不把 datasource、model、MCP OAuth 或連線字串完整物件傳到 React。`/models` 只投影 id/name/model/provider。
- [x] fork source 新增 System & integrations workspace 與側欄入口；排版以來源分區、獨立部分錯誤、Refresh/Retry、component list disclosures、DB/model/interface/MCP cards 呈現。Langfuse 以 local link 展示；Gateway／Backstage／report 標記為 AgentOS native API 無法判斷，未假稱可用。
- [x] `pocs/agno/agent-ui.patch` 已含 System Explorer、API/types、routing、store 與 Sidebar；Docker production build 完成並部署。最終 image：`sha256:1a182c1c701b30c0ba4e1b6013585e479323623837f7dde26d32fdf95f86ebd1`。本輪 source patch 變更外部整合卡狀態，Docker build 重新執行 `git apply --check`、patch apply、Next compile（25.9 秒）、lint/type check、static generation 全數成功。
- [x] Patch 產生注意：以 PowerShell `Set-Content` 寫 diff 會將 patch 轉為 CRLF，Docker `git apply --check` 對多個檔案失敗。已改用 `git diff --binary HEAD --output=../pocs/agno/agent-ui.patch` 直接由 Git 輸出原始 LF patch，隨後 Docker patch apply 與完整 production build 通過。
- [x] Compose 驗收：`factory-agent-ui` Up（port 3000）、`factory-agentos` Up（port 7777）、`factory-agno-db` Up (healthy)；Langfuse web／worker 及相依服務仍在執行。本輪沒有刪除任何 image、volume 或容器。
- [x] 使用者已預先輸入 key；Docker UI recreate 後頁面 reload 清除記憶體中的 Token，因此依既有授權由本機 `.env` 重新填入本機 Agent UI。瀏覽器只顯示遮罩，並未把 Token 輸出到聊天、文件或截圖。
- [x] Desktop 瀏覽器實際驗證 System & integrations，`/health`、`/info`、`/config`、`/models`、`/factory/revision` 均成功載入：Agno 2.9.0、health OK、26 Agents、3 Teams、2 Workflows、1 Session DB、0 interfaces、1 model（MiniMax-M3.1-Flash / OpenAI），MCP disabled；Factory revision `bdcc8db58b2161b3` 的 component counts 與 AgentOS config 一致。截圖：[System Explorer Desktop](screenshots/system-explorer-desktop.jpg)。
- [x] 視覺核對：Factory registry snapshot 是獨立卡片；config 失敗不會遮住 revision 成功資料。Agents／Teams／Workflows 清單各自可展開；外部 Gateway／Backstage/report 未從 AgentOS config 推測可用。外部整合原先錯誤顯示綠色 `Loaded`，已改為中性 `Not checked` 並在最終 Docker image／截圖確認。截圖中的 Token 維持遮罩。
- [ ] System Explorer 的 375px viewport、注入部分來源失敗，以及外部服務健康／連線尚未驗；因此 F16 整體與 P2.4 保持未完成。
- [ ] 不要將 config 原始 JSON、key、模型供應商憑證、DB DSN 或 MCP OAuth 欄位加入 UI／截圖。外部服務健康尚未透過服務端 readiness check 驗證。

## P2.2 Metrics unknown-table error checkpoint（2026-11-21）

- [x] 在 Docker UI 的 Observability → Metrics 選定具名 DB，輸入不存在的 table `codex_missing_table_verification` 並載入。UI 收到 AgentOS `500 Internal Server Error`，保留篩選內容並顯示 Retry。
- [x] 錯誤狀態的桌面排版清楚顯示 table、日期區間、DB 範圍、錯誤與 Retry；已保存畫面：[Unknown Metrics table error](screenshots/observability-metrics-unknown-table-error-desktop.jpg)。
- [x] 此測試是唯讀 GET；實際 API 回 500，文件按實際狀態記錄，未將其描述為 404。

## 使用者要求：Agno 升級至 3.2.1（2026-11-21，進行中）

- [x] 以官方 GitHub Releases 及 PyPI 核對：`agno==3.2.1` 已於 2026-11-17 發布且標為最新；目前 POC runtime 與 requirements 仍是 2.9.0。
- [x] 建立詳細升級與 UI 調整 checklist：[Agno 3.2.1 upgrade plan](agno-3.2.1-upgrade.md)。
- [x] 初步查 code migration：`Workflow(id=...)` 已符合 v3；搜尋未發現 v3 migration guide 列出的舊 HITL kwarg、移除 Agent/Team kwargs、`reasoning=True`、`continue_run(updated_tools=...)`、舊 JWT/MCPToolbox 參數。
- [x] 唯讀盤點 v2 schema：Agno tables 在 PostgreSQL schema `ai`，13 個 schema versions 均為 2.5.6；`agno_sessions` 有 47 筆、JSON runs 共 59 筆、metrics 3 筆、learnings／memories／knowledge／approvals／evals／components／schedules／service accounts 為 0，尚無 `agno_runs`。
- [x] migration 前備份已建立並通過 `pg_restore --list`，容器來源與本機副本 hash 一致。大小 1,903,799 bytes、SHA-256 `dba58add7cebf8f86e90d7e201486ccae0b57d651d6df202c14092ba8d27a4ea`；本機位置 `pocs/agno/backups/agno-db-v2-before-3.2.1.dump`，由 `.gitignore` 忽略。
- [x] `pocs/agno/requirements.txt` 已 pin `agno[os]==3.2.1`，`requirements.lock` 已用 Python 3.12 重解析；確認 lock 內 `agno==3.2.1`、`agnoctl==0.2.1`、`fastapi==0.165.0`、`pydantic==2.14.4`。uv 初次受隔離 cache 寫入及 DNS 限制，改在 POC 目錄設 cache 並允許 PyPI 連線後成功。
- [x] Docker AgentOS 3.2.1 production build 成功，image `sha256:833882bc1e024e1acbc6ad9ce953c5b4b1bb0239451ea85f28a1ab17f8b013f2`；Compose one-shot import 確認 `agno.__version__=3.2.1`、Factory app title `Agno AgentOS`、32 routes。首次 import 發現 v3 `Step` 移除 `on_error`，改為 `skip_on_failure=False` 並成功重載所有 Factory workflows。
- [x] 使用者要求前已停唯一 Agno DB writer `factory-agentos`；以 Agno 3.2.1 `MigrationManager(PostgresDb(...)).up()` 成功將 storage schema 遷移至 3.0.0。migration 複製 59 legacy session runs 至 `agno_runs`，re-key 掃描 0 learning rows 並回報所有 error/conflict counters 皆 0。
- [x] 遷移後唯讀核對：47 sessions、`agno_runs` 59 rows、legacy JSON backup runs 59、3 metrics、0 learnings；`agno_sessions.runs` 欄位仍存在，未執行 cleanup。15 schema-version records 為 3.0.0；空的 `agno_component_configs`、`agno_component_links`、`agno_service_accounts` 仍為 2.5.6，MigrationManager 無對應 migration；保留原表而未手動修改 schema。
- [x] 當時嘗試推送使用者指定的 `cletuslee/agno-agentos` namespace，但登入帳號 `cletus` 沒有權限；使用者隨後建立正確 repository `cletus/agno-agentos`，後續發布與驗證記錄見本文件最新 checkpoint。
- [x] 舊 Docker images 清理曾暫緩至 3.2.1 驗收完成；最新狀態與移除的明確 ID 見本文件最上方 Agno 3.2.1 checkpoint。

## Agno 3.2.1 image 發布、Compose 與 System Explorer checkpoint（2026-11-21）

- [x] 版本契約已直接從運行中的 `factory-agentos` 唯讀核對：`/info` 200、`agno_version=3.2.1`；`/config` 200，包含 1 個 `available_models` 摘要；`/openapi.json` 200、OpenAPI 3.1.0、93 paths／134 operations。`/models` 在 v3 回 404，UI 改由 `/config.available_models` 讀取並保留 v2 fallback。
- [x] 3.2.1 `GET /sessions/{session_id}/compactions` 對既有 Workflow session 回 200、空 array；schema 欄位為 `id`, `run_id`, `messages_compacted`, `tokens_before`, `tokens_after`, `created_at`, `archived`。UI 顯示成功 empty state，沒有 compaction summary／archived messages 假資料。
- [x] 使用者建立 Docker Hub repository `cletus/agno-agentos` 後，Agno image 已發布 tag `3.2.1`。本機 image config ID：`sha256:833882bc1e024e1acbc6ad9ce953c5b4b1bb0239451ea85f28a1ab17f8b013f2`；遠端 manifest digest：`sha256:6a13d301661dcef023c1d7d0d5264cd369a68c1cca4cb362698ba6749e77df70`。
- [x] 以未登入 Docker Hub API 確認 repository `is_private=false`、tag `3.2.1` 存在，架構為 linux/amd64。任何人可 `docker pull cletus/agno-agentos:3.2.1`；原先誤用的 `cletuslee/agno-agentos` push 被拒，沒有對該 namespace 建立遠端 tag。
- [x] 預設 `docker-compose.yml` 現在引用公開 image `cletus/agno-agentos:3.2.1`，已移除 AgentOS 預設本機 build；新增 `docker-compose.build.yml` 作為明確的本機重建 overlay。預設 `docker compose config --images` 只列出公開 AgentOS tag，`docker compose pull agentos` 成功。
- [x] 用預建遠端 tag recreate `factory-agentos` 後，Docker inspect 顯示 `.Config.Image=cletus/agno-agentos:3.2.1`、image ID 與已發布 image 一致；容器內 `agno.__version__=3.2.1`，Compose healthcheck healthy。
- [x] 使用者已在 ChatGPT in-app browser 重新輸入本機 Agent UI Token。System Explorer 顯示 `HEALTH OK`、Agno `3.2.1`、26 Agents、3 Teams、2 Workflows、Factory revision `bdcc8db58b2161b3`、1 session DB、1 model；Token 欄只有遮罩。新截圖在工作階段工具輸出中目視確認，但無法透過本次瀏覽器工具存成 repo 檔案。
- [ ] `docs/screenshots/system-explorer-3.2.1-desktop.jpg` 尚未存在；不要以舊版 `system-explorer-desktop.jpg` 替代。375px System／Runs 新版本驗收也待有生效的 viewport override 後執行。
- [x] 已解除錯誤候選 namespace `cletuslee/agno-agentos:3.2.1` 的本機 alias；仍在使用中的底層 image 維持 `agno-factory-local-agentos:latest`／`cletus/agno-agentos:3.2.1` 兩個 tag。

## 2026-11-22 Markdown checklist audit (historical pre-recheck snapshot)

- [x] 此較早 audit 曾統計各文件未勾選框；該數字包含歷史 checkpoint，且後續驗收已更新狀態，不再代表目前待辦數。請以本文件最上方最新 checkpoint 和能力計畫逐項未完成清單為準；勾選狀態不代替執行證據。
- [x] 此 pre-recheck checkpoint 的 ChatGPT in-app browser System 頁顯示 AgentOS 3.2.1、26 Agents／3 Teams／2 Workflows、1 session DB、1 model；Approvals／Schedules／Components／Queue／Service Accounts 為 HTTP 503，Registry 當時只有 HTTP 200 status card，沒有 records list/filter/pagination。這個 Registry 狀態已被 image `0052fa…` 的授權清單驗收取代；現行部署為 c2f78c7。Langfuse、Gateway、Backstage 均為 health-only HTTP 200。
- [x] 本次 System 畫面已在 browser tool output 擷取並目視檢查；該工具未提供可寫入 repository 的 screenshot file API，因此沒有新建圖檔。
- [x] 較早 checkpoint 的 Docker Engine named pipe permission denied 已在本輪恢復後續驗；Docker CLI 確認 `factory-agent-ui` running、image ID `sha256:0052fa5430b7eed45fc2d78eb0e29f04f71c7cb76c57252fb28eb7927ade7967`，ChatGPT browser 授權 System／Registry UI 與該 image 相符。
- [ ] 能力計畫整體未完成。主要缺口仍是真實 Knowledge／Memory／Learning／Trace／eval 資料、Approvals／Schedules 等 503 能力、disconnect／跨 DB 深連結與 125%／完整鍵盤 focus 驗收、operation-level API contract、以及 repo 截圖匯出。

## 2026-11-22 375px System／Runs verification

- [x] ChatGPT in-app browser 啟用 viewport override 375×844，從 System 頁依序檢視部署資訊、元件／storage／model／interface、管理狀態與外部整合；再以側欄切換 Runs，保留遮罩 Token 與既有 URL deep link。System 直向卡片未見水平溢出。
- [x] Runs 載入 Continuous Improvement：1 session；run `5898977d-3a48-4af6-a0a8-12e618b78724` 為 COMPLETED，顯示 6 step results、10 executor runs、0 events、Not paused；Session compactions 成功空集合。窄版 screenshot 已在 browser tool output 顯示，未能另存 repo。
- [x] 此較早 System／Runs 檢查結束時已 reset viewport；後續 production image recheck 又設為 375×844，使用者 Escape 停止後續操作，因此目前 viewport override 仍在 375×844，尚待下次允許的 browser 操作 reset。Docker CLI image ID 核對結果見本文件最上方 checkpoint。
- [x] 嘗試以 ChatGPT in-app browser 的 Ctrl+Shift+= 兩次設定實際 zoom、再用 Ctrl+0 還原；畫面沒有可辨識的 viewport／排版變化，工具也沒有縮放狀態讀取介面。實際 125% zoom 仍維持未驗，不以快捷鍵嘗試或 CSS viewport 代理勾選通過。
- [x] 完成 P3.2 唯讀寫入責任評估並記錄於[能力計畫](agent-ui-capability-plan.md)：列出 run、approvals、schedules、Knowledge、Memory／Learning、eval／metrics refresh、Studio／service account／component／DB migration 的權限、精確目標、影響及防重複原則。沒有執行寫入或加入寫入按鈕。

# Agno POC 的 Agent UI 版面與功能實作清單

規劃與契約基準更新日期為 2026-11-23（台灣時間）。本文件以 `pocs/agno` 的 Agno **3.2.1** Docker 部署為基準。目標是讓使用者在 Agent UI 找到已部署元件、理解設定，並從元件追到實際執行與證據。

`[x]` 表示該條設計已定案、工作已完成或驗收已有證據，依條目所寫的範圍判定。`[ ]` 表示該條仍有實作或驗收待辦。F01～F17 與各階段的主項在整項交付後打勾，已完成的部分列在下方子項。升級前的驗收保留版本標記，3.2.1 的覆驗範圍以[新版驗收證據](agent-ui-verification-evidence.md#agno-321-ui-verification)為準。

## 2026-11-23 目前交付狀態

- 電腦重新啟動後，Docker Engine 已由 Docker CLI 驗證可用，Compose 以 `up -d --wait --no-build` 恢復服務，沒有為重開機重建 image。最新 Agent UI production image `sha256:335cab6a78137c56a89a6838968edaf798bd32b35ed98f774065bf3267924bb9` 於 2026-11-23 建置並部署；UI `/` 與 `/api/agentos/health` 回 200、未授權 `/api/agentos/config` 回 401，Agno DB healthy，AgentOS 為 3.2.1。System UI 授權載入 26 Agents／3 Teams／2 Workflows、69 筆 Registry（7 頁）、1 個 session DB；Langfuse、Gateway、Backstage health 均回 200。Approvals、Schedules、Components、Queue、Service Accounts 的授權 GET 仍各回 503。
- 本輪用 ChatGPT in-app browser／Docker fixture 完成 Overview 空集合、403、503 Retry、斷線 Retry、快速 DB A→B 舊回應隔離、Runs socket drop 後 Retry、跨 DB／不存在 component 深連結，以及 Workflow 未知 step 標籤驗收；Backstage Catalog Graph 也已設定根節點並確認顯示節點與關係。具體證據與限制見[實作紀錄](agent-ui-implementation-log.md)和[新版驗收證據](agent-ui-verification-evidence.md)。
- F07 Runs `db_id` 初始化修正已由正式 Docker build 套用及部署至上述 `335cab6…` image；ChatGPT browser 直接載入具名 DB 的 Workflow session/run 深連結後，URL／DB selector 保留指定 `db_id`，既有 session、完成的 run、6 個 step results 和 10 個 executor runs 均能還原。Production 只有 1 個 session DB，跨 DB 隔離仍以先前的 bind-mounted fixture 證據為準。
- **能力計畫尚未整體完成；V06 交接項已完成。** 真實 Memory／Learning／Knowledge／Trace／Eval fixtures 不足；Approvals、Schedules、Components、Queue、Service Accounts 等回 503；Langfuse run 關聯仍未驗；完整 API operation sampling、真實 stream abort、125% 縮放、完整跨頁鍵盤稽核和新版截圖 repo 匯出仍有缺口。外部健康檢查的失敗隔離已在獨立 Docker network 驗收。P3 的模型執行與資料寫入需具體目標及操作授權，未以空資料或合成結果代替完成。各功能缺口仍依下方未勾選的主項／子項追蹤。

## 接手起點

- [x] 目標為 `pocs/agno`（Langfuse 版）。Compose 預設 Agent UI 在 `localhost:3000`、AgentOS 在 `localhost:7777`、Langfuse 在 `localhost:3001`。辨認方式見 [POC README](../README.md) 和 [Compose](../docker-compose.yml)。
- [x] 現行 [Dockerfile.ui](../Dockerfile.ui) 固定從 fork commit `817a009b3d7e407b17b48872f5bbf1c5055b5955` 建置，並從本 POC 的 `agent-ui.patch` 套用差異。 fork 已含 Agents、Teams 與 Workflow 檢視。[前一個 POC 的交接](../../agno-tempo/docs/agent-ui-workflow-tasks.md) 僅供參考，正式驗收在本 POC 執行。
- [x] AgentOS 已升級到 3.2.1。[版本需求](../requirements.txt) 固定 `agno[os]==3.2.1`，[Python lock](../requirements.lock) 固定解析後版本。預設 Compose 拉取公開的 `cletus/agno-agentos:3.2.1`，本機重建使用 [build overlay](../docker-compose.build.yml)。PostgreSQL 已遷移至 Agno storage schema 3.0.0，原 session runs 已複製至 `agno_runs` 並保留舊欄位。[升級與部署紀錄](agno-3.2.1-upgrade.md)
- [x] [AgentOS 入口](../app.py) 提供 `/factory/revision`、完整 Skill 目錄 `/factory/catalog` 及 Workflow、Agent、Team 三類 Factory 唯讀詳情路由，沿用 AgentOS 認證。2026-11-23 重啟後 live OpenAPI 3.1.0 仍有 **94 paths／135 operations**。路由、參數與 schema refs 見 [3.2.1 inventory](agentos-api-openapi-3.2.1.md)，已執行的查詢見 [API 契約](agentos-api-contract.md#321-live-contract-checks)。
- [x] 本 POC 有三種不同的資料。Factory registry 描述部署的設計。AgentOS 提供元件設定及其保存的 session、run。Langfuse 收到的 observations 能佐證某次模型呼叫、工具或委派。每個頁籤顯示資料來源，歷史執行若缺 revision 則標「當時版本未知」。[定義載入順序](../integration/registry.py) · [POC 整合與操作](../README.md)
- [x] 本計畫已於 2026-11-21 完成 review，實作與 Docker 驗收已開始；「大多數功能可見」以功能家族為單位。下表每個家族都要有查看入口或在「系統 → 功能支援」有具體原因。最低可用版本要能從元件一路找到一筆執行及證據。寫入、管理和會啟動模型的動作另有交付條件。功能範圍參考 [Agno 官方 API 概覽](https://docs.agno.com/agent-os/using-the-api.md) 與 [官方文件目錄](https://docs.agno.com/llms.txt)。官方現行文件涵蓋後續版本，路徑及 schema 以此 POC 的 OpenAPI 為準。

## 版面決策

- [x] 側欄固定順序為「總覽」、「工作區」（對話、Sessions 與 Runs）、「元件」（Agents、Teams、Workflows）、「資料」（Knowledge、Memory 與 Learnings）、「觀測」（Traces、Metrics、Evaluations）、「營運」（Approvals、Schedules）、「系統」。Tools、Skills、Models、DB 與整合從相關元件或系統頁進入。外部系統集中在對應詳情的連結。
- [x] 沒有指定目的地時開總覽。明確指定 view 的深連結優先；舊版只有 agent／team、session 或 db_id 的網址仍按原 Chat 邏輯還原。頁首保留目前 AgentOS、連線／認證狀態與重新整理。總覽先顯示元件數、部署 revision 與「查看 Sessions」入口；只有後端能在已知範圍內排序時才顯示「最近執行」，並標出 DB、時間窗與涵蓋範圍。
- [x] 桌面採「左側導覽 → 中間清單或工作畫布 → 右側選取項目」。元件很多時清單可搜尋與收合。長內容獨立捲動，麵包屑保留層級。Workflow 的「設計」顯示步驟樹與分支，「執行紀錄」顯示已保存的 Runs，必須選定一筆才著色執行路徑。
- [x] 詳情優先顯示名稱、可複製的完整 ID、狀態與來源，再用頁籤容納定義／設定、關聯、執行紀錄。結構化欄位先行，允許公開的長文或 JSON 可摺疊。資料缺漏要精確到欄位或來源。
- [x] 在窄版維持單一主要任務。側欄可收合，清單可退回，詳情改抽屜或全頁。用**分支容器可用寬度**決定平行節點的欄數，寬度不足時改直排；true/false 與執行順序仍有文字標籤。關閉後回到同一節點、捲動位置與鍵盤焦點。
- [ ] 實作共通導覽。深連結帶工作區代號、view、元件 type/id、db_id、session type/id、run_id 與頁籤等該頁必要欄位，工作區代號由本機已設定的 endpoint 對照。過期 ID 顯示找不到並提供返回入口。測舊 Chat 書籤、新 run 直達、重整及返回原節點。URL 只存可分享的識別與篩選。
  - [x] 最新 Sidebar patch 已為 overview、chat、workflows、agents、tools、runs、data、observability、system 定義 query allowlist；從 Runs 切 Overview／System，或 System 切 Tools，切換後與資料 hydration 完成後都會清除不屬於目的頁的舊 filters。此項只完成 view query state 正規化；workspace endpoint 對照、所有深連結欄位／舊書籤及不存在 ID 的整體回歸仍待驗。

以「查看設計，再找一次實際執行」為例，桌面與窄版採下列排列。清單只在選取元件時占用空間。

```text
桌面    全域頁首   AgentOS／連線狀態                         重新整理
        左側導覽 │ Workflows > Software Delivery             │ 節點詳情
                 │ [設計] [執行紀錄]                         │ Testing / factory-09
                 │ 步驟樹、條件、並行群組 或 所選 run 的時間軸 │ 定義、設定、關聯

窄版    選單 → 可搜尋的 Workflow 清單 → 設計（分支及節點直排）
                                         ├ 點節點 → 詳情 → 關閉回原位置
                                         └ 執行紀錄 → 選 run → 時間軸／Trace
```

## 功能清單與逐頁驗收

每項是一個可獨立驗收的頁面或頁籤。「可用」以所選部署、資料庫與使用者的實際回應判斷。F01 的 Overview 已驗 DB reload、canonical URL／Browser Back、逐來源 401／Retry／恢復、成功空 state 的合成 fixture，以及 Approvals／Queue 的實際設定不可用狀態；目前真實部署有近期 sessions，沒有 production empty response 可觀察。F03～F05、F07～F17 的完整交付依各項缺口追蹤；F06 的唯讀 Tools／Skills／Models 目錄、schema、反向查詢及 29/29 runtime components 覆蓋已完成。F08 已有原本的 Chat 執行；F13 現有原生 Evals 唯讀清單與本機實驗 runner，但尚無已執行的 Langfuse A/B 結果。下方階段表記錄已交付的子項與剩餘驗收。

- [x] **F01 總覽與能力**　工作區名稱、版本、Agents／Teams／Workflows 數量、最近 Runs、需處理項目。各區可獨立重試。

  資料與驗收：AgentOS 清單與 Factory revision 分開取值。點 Workflows 數量進清單，總數與同來源一致。沒有全域 run 來源時以 Sessions 入口交付。待處理數量也須對應已配置的佇列，無來源時說明原因。

  - [x] 3.2.1 Overview 已加入 POC patch。分開載入 AgentOS health、runtime info、白名單化 config、Factory revision 與最近 5 筆 sessions。以 config 回應計算 component counts，Factory revision 獨立顯示。Sessions 使用 `sort_by=updated_at`、分頁上限 5，支援選 DB；各來源有各自的 loading／error／Retry 狀態。沒有全域 Recent Runs API 時顯示近期 Sessions 並提供 Runs 入口。
  - [x] Docker production build、部署及核心 browser 驗收：26 Agents／3 Teams／2 Workflows、AgentOS 3.2.1、Factory revision、1 session DB、近期 5 sessions 都以本機 3.2.1 容器載入。Token 遮罩；無 Token 時 health／info 仍成功，Factory／config／sessions 各自回報 401。資料驗收 image `sha256:8f1269…` 已在 ChatGPT in-app browser 的 375×844 viewport 覆驗 Overview、Runs、Tools、Skills、Models、Observability 與 System；後續 image `sha256:4f57e9…` 加入 sidebar Escape／焦點返回；前一 image `sha256:bab1260…` 加入 endpoint 切換隔離；image `sha256:7809386…` 修正初始化重複請求；image `sha256:3e55f72…` 加入 System 外部服務健康查詢並保留先前行為。Overview document/body 寬 375px、主內容 client／scroll 寬 334px，均無水平溢位。[實作紀錄](agent-ui-implementation-log.md#最新接手點2026-11-22)
  - [x] 精確 session 導覽已加入 POC patch：從 session type 對應 Agent／Team／Workflow ID 為 component ID，將 type、component ID、session ID 與所選 DB 傳到 Runs；session 名稱最多兩行。
  - [x] Docker browser 實驗精確 Workflow session 深連結：選定 session 與其 run IDs 一致，顯示 1 session、1 個 `COMPLETED` run、6 step results／10 executor runs。375px viewport 下 document 寬度等於 viewport。
  - [x] DB selector 切換至 `AgentOS default`：Overview 設 `overview_db=default`；點 `Open session` 後 Runs 移除 `db_id`、保留 `overview_db=default`，仍可載入同一筆 session／run。原選定具名 DB 的 Overview／Runs 載入也已見證。
  - [x] 具名 DB 的 Overview 重整後仍以 `overview_db=<db_id>` 選取同一 DB，重新輸入本機 Token 後五筆近期 sessions、Factory revision 與 component counts 均成功還原。Token 不會在重整後持久化，欄位仍遮罩。
  - [x] Runs→Overview 導覽改成 canonical URL：保留 `view=overview` 與所選 `overview_db`，清掉舊 `session_type`、`component_id`、`session_id`、`db_id`、`agent`、`run_id`。瀏覽器 Back 會恢復原 Workflow session/run IDs、DB 選取與 run detail；重整 Overview 後亦保留 DB 選取。
  - [x] 逐一點擊 Factory revision、Recent sessions、Registered components 的 Retry。無 Token 時三者各自顯示 401；health 與 runtime info 仍成功顯示。依本機授權重新輸入 Token 後三個來源均重新載入成功，錯誤卡不會阻止其他來源顯示。
  - [x] 最新 UI image `sha256:7809386…` 以 ChatGPT in-app browser 在 375×844 與 300×675 覆驗無 Token Overview；兩個尺寸的 `innerWidth`、document `scrollWidth`、body `scrollWidth` 均等於 viewport，health 顯示 OK，受保護來源獨立顯示 401／Retry。截圖於本輪 browser tool output 擷取及目視確認；未存 repo 檔案。
  - [x] 本輪 3.2.1 Overview 窄版與桌面畫面已由 ChatGPT in-app browser screenshot API 擷取並目視檢查；repo 圖檔匯出限制統一追蹤於 V05，不在 F01 重複列待辦。
  - [x] ChatGPT in-app browser 的隔離 Docker fixture 對 `GET /sessions?db_id=default` 回 200／空 `data`；Overview 顯示「No sessions were returned for this database」。這驗證 UI 的成功空狀態，不代表目前真實 AgentOS 有成功空的 sessions 回應。
  - [x] 新增 Pending work sources 卡片，獨立唯讀查詢 `GET /approvals` 與 `GET /queue`、各自提供 Retry，並由 Refresh all 一併重查。Agno 3.2.1 授權查詢回 503 時明確顯示目前設定不可用，不標成空集合；若之後回 2xx，因 OpenAPI 沒有清單 schema，UI 也不捏造待處理筆數。production image `sha256:c2f78c7…` 的 ChatGPT in-app browser 已實際看到 Approvals／Queue 各自 HTTP 503；本輪再按 Approvals 的 Retry，只有該來源的檢查時間更新，Queue 保持原狀。畫面只由 ChatGPT browser screenshot API 擷取至工具輸出，沒有擷取整個桌面；repo 圖片匯出限制見 V05。

- [ ] **F02 對話**　沿用 Agent／Team 切換、新對話、串流、工具事件、引用、可用的檔案與多媒體。結束時顯示 session/run 連結；中斷時保留已收到內容。

  資料與驗收：沿用 fork 的 Chat、SSE 及 session loader。回開已保存對話能還原訊息。只呈現 API 明確提供的公開推理摘要／事件。

- [ ] **F03 Agents**　列表可依名稱、ID、模型搜尋（已在最新 image 實作並驗證）。詳情含角色、輸入／輸出、instructions、模型與 provider、tools、註冊 skills、memory、knowledge、history、output schema 等已提供的設定，以及所屬 Team／Workflow。第一版已加入 Factory definition 與完整 AgentOS runtime JSON 摺疊區；Testing Agent 的角色、I/O、Skills、instructions、模型及 runtime tools 已在 Docker UI 驗收。API 未回傳的 Knowledge／Memory 明確標示不可用；Workflow 引用矩陣已唯讀核對，完整設定欄位與失敗隔離仍待續。

  資料與驗收：AgentOS runtime 與 Factory 定義分區載入。以 Testing 對照實際 ID 與兩邊回應，一方 404 仍可看另一方。分辨角色預設 skill、工單提供的 skill 與本次實際讀取紀錄。
  - [x] Image `sha256:c2f78c7…` 的搜尋欄支援不分大小寫、去除前後空白，並比對名稱、ID、model name／ID／provider。ChatGPT browser 375px 實測 `factory-09` 只留下 Testing Agent；模型 `MiniMax-M3.1-Flash` 顯示 26 個 Agent，provider `OpenAI` 亦能找到該組模型元件；切至 Teams 後搜尋欄標籤與清單正確切換，搜尋相同模型顯示 3 個 Team。此子項完成；其他詳情欄位仍待盤點。[驗收證據](agent-ui-verification-evidence.md#agno-321-ui-verification)
  - [x] 只讀 API audit 核對 Testing Agent 的 Runtime keys 與 Factory fields／2 Skills，並核對 Knowledge Team 的 runtime mode／model／members／tools 與 Factory 4-member definition。AgentOS Agent／Team 詳情不直接提供反向 Workflow links；兩個 Factory Workflow definitions 可由 UI 讀取後安全計算引用關係。
  - [x] Agent 詳情的 Factory Workflow references section 已加入並 build 至 production image `sha256:813fe12…`；ChatGPT browser 以 Testing Agent 驗到 Software Delivery reference。2026-11-22 唯讀覆核兩個 Workflow definitions 均成功載入：26 Agents 中 13 個被引用，3 個 Teams 中 3 個被引用，未解析的 Agent／Team references 為 0。UI 範例只實際開啟 Testing Agent；其餘個別詳情畫面與 definition failure 隔離仍未逐一驗。

- [ ] **F04 Teams**　顯示 Team prompt、模型、成員、可用的委派模式、子成員與引用它的 Workflows。點成員進詳情，可返回原 Team。Observability Team 的 instructions、coordinate mode、模型、delegate tool、四個 members、runtime member IDs 和兩種 JSON disclosure 已在 Docker UI 驗收；2026-11-22 production image 已於 ChatGPT browser 完成成員→Agent→返回原 Team 的 URL／內容驗收。所有 Team 的 Workflow 引用矩陣已唯讀核對；單次實際委派與其他 Team 的逐頁詳情仍待續。

  資料與驗收：原生 Team detail 加 Factory 成員。測試 Knowledge Team → Research，快速由 Agent 切換 Team 時不閃現舊詳情。已註冊成員與單次實際委派分別呈現。
  - [x] Team 成員點進 Agent 詳情時，`factory_return_team` query 保存來源 Team，`ComponentDetails` 顯示返回按鈕，並能從 URL 還原返回目標。2026-11-22 以 production image `sha256:0052fa5430b7eed45fc2d78eb0e29f04f71c7cb76c57252fb28eb7927ade7967` 在 ChatGPT browser 實際完成 Observability Team → `factory-21` Agent → Back to Observability Team；URL 保留／還原 team ID 並在返回時清除 return query。
  - [x] Team 詳情的 Factory Workflow references 已 build 至 production image `sha256:813fe12…` 並與 Agent 共用；ChatGPT browser 驗到 Knowledge Team 的 4 個 members、delegate tool、Software Delivery reference，並由 Research 返回原 Team。2026-11-22 唯讀覆核全部 3 個 Team 與 2 個 Workflow definitions：所有被引用 Team 都能對上 runtime ID，無未解析 reference。其他 Team 逐頁畫面、快速切換無舊資料閃現與部分 definition failure 隔離仍未驗。

- [ ] **F05 Workflows**　概覽含 revision、步驟、使用元件。圖與樹狀清單可互切；節點顯示完整路徑、類型、條件、executor、並行成員、前後步驟。長名稱可換行。

  資料與驗收：以原生清單／詳情建立設計樹，Factory 平行補上部署定義。驗收兩個 POC workflow、兩層 false 分支及兩個 parallel 群組。以不同 revision、重試與缺事件的 run 測試圖上著色：需證實同 workflow、對應歷史版本與節點識別；當時定義內名稱唯一才可當識別。每次嘗試或迴圈迭代分別保留。無可靠對應時只畫該 run 的時間軸，缺事件顯示「未取得」。Loop、Router、未知節點可用具名 fixture 驗收。
  - [x] 2026-11-22 對兩個 Workflow 的 AgentOS runtime 與 Factory definitions 做唯讀比對，兩者均回 200。Software Delivery 有 22 個節點、2 個 Condition（各有 true／false branches）及 2 個 Parallel 群組（各 3 個 children）；Continuous Improvement 有 6 個根節點。UI 現在提供 Tree／Graph 切換、分支／並行標籤、所選節點完整 path/type 與可點選的 Previous／Next／parallel sibling 關係。未知 step type 有明確的 `Unsupported step (<type>)` 標籤；此修正已於 image `sha256:d2eb8f…` 完成 production build。
  - [x] 隔離 Workflow fixture 回傳 `loop`、`router`、`custom_step` 三種非原生型別；ChatGPT browser 實際在 Tree 與 Graph 顯示 `Unsupported step (loop)`、`Unsupported step (router)`、`Unsupported step (custom_step)`。這只驗證未知標籤與排版，不代表未知執行語義或子分支可解析。
  - [x] ChatGPT browser 驗到 Software Delivery Graph 的 Readiness `TRUE`／`FALSE` branches、兩組各 3 個平行節點；選取 Code Proposal 時 inspector 顯示 Previous／Next 與 Infrastructure／Integration Proposal siblings 的穩定 path。Tree／Graph 可切換。此為較早 desktop-only 截圖；375px 驗收另列如下。
  - [x] 2026-11-22 ChatGPT in-app browser 以 375×844 隔離 fixture 驗 Graph 的 3 個平行子節點單欄直向排列；每張卡寬 272px、X 座標相同，`innerWidth`／document／body 寬度皆為 375px，無水平溢位。unknown step labels 仍正常顯示。這證明窄版欄數行為，不代表 Continuous Improvement production definition。
  - [x] Tree／Graph inspector 的只鍵盤啟動：Tab 聚焦節點後按 Enter 開啟 dialog；焦點先落在 Close，Tab／Shift+Tab 循環停留在 dialog，Escape 關閉並返回觸發節點。Close 按鈕返回焦點也已驗。
  - [ ] Continuous Improvement production Graph 與歷史 run revision／highlighting 尚未完成驗收。

- [x] **F06 Tools、Skills、Models**　元件內按工具名稱查看用途、參數 schema 與來源，Skill 可看說明、instructions 與使用它的 Agent，模型可看 ID、provider、可公開參數。支援從目錄反查元件。

  資料與驗收：Factory 反向關聯由後端以完整部署快照產生。測試沒點過的 Agent 也會列入「使用此 Skill」。Runtime 只查過部分元件時標明範圍，工具以 endpoint、所屬元件種類／ID 及工具識別區分。同版同名但 schema 不同的工具應可分別查看。相容 tools 陣列和包在物件內的格式。實際呼叫次數另取 run／trace。
  - [x] Agent／Team 詳情既有 Runtime tools 名稱／說明、Agent Factory Skills 說明／instructions、模型 provider／model；原始 AgentOS runtime 與 Factory definition 各自保留 disclosure。此子項記錄既有詳情頁；完整 F06 目錄覆蓋見下方 29/29 components、108 tools、14 Skills、Models 與反查驗收。
  - [x] Runtime tool `parameters` schema 的可收合 disclosure 已加入 POC patch，沒有 schema 時顯示 AgentOS 未提供。Docker production build、lint／typecheck 與 static generation 成功；live `GET /agents/factory-09` 200，4 個 tools 均帶 `parameters`，schema 有 `type`／`properties`／`required`。
  - [x] 3.2.1 Docker UI 選取 Testing Agent `factory-09`，顯示 4 個 runtime tools 的 schema disclosures；展開 `load_work_item_context` 可讀 `object`、4 個 properties、`required: work_id`。前一版 image `sha256:47aa9b…` 已在 375×844 驗 schema 欄無水平溢位、長內容在自己的 pre 區垂直捲動；`sha256:8f1269…` 驗目錄 375px 版面及來源，後續 image `sha256:4f57e9…` 加入 Sidebar 鍵盤收合；前一 image `sha256:bab1260…` 保留目錄並加入 endpoint 切換隔離。[本輪實作紀錄](agent-ui-implementation-log.md#最新接手點2026-11-22)
  - [x] Docker production build image `sha256:8f126975d3f2ac3f600f30604607996f16c63c2e0edd5054eb835bdac570feff` 的 Tools 目錄實測：AgentOS `/config` 所列 **29/29 components** 成功載入，合計 **108 Runtime tools**。每張卡包含描述、Agent／Team 來源種類與 ID、runtime endpoint、tool identity 及可展開 `Parameter schema`。
  - [x] 搜尋 Testing 來源得到 4 個 Runtime tools；四個 schema 都可展開。`load_work_item_context` 顯示 4 properties，`work_id` 必填；其他三個目前回傳空 properties／required 的 object schema。
  - [x] `/factory/catalog` 以完整 Factory snapshot 回傳 14 Skills、revision、description、instructions 及每個 Skill 的全部 Agent references。`model-usage-cost` 反查出 Optimization／factory-19 與 Cost Control／factory-27；點擊 Cost Control 可深連結並選取正確 Agent。
  - [x] Models 目錄從 `/config.available_models` 顯示唯一模型 `MiniMax-M3.1-Flash`、provider `OpenAI`，並列出 29 個 runtime components 的使用關聯。Agno 3.2.1 的 `GET /models` 回 404，`model` 及其他額外 public parameters 均未由可用 API 回傳，UI 明確顯示未提供，不捏造欄位。
  - [x] `sha256:8f1269…` 的 Tools、Skills、Models 目錄均在 375×844 ChatGPT in-app browser 覆驗；共用主內容寬 323px，長 Skill 與 Agent reference 可在欄內換行，未超出 375px viewport。前一部署 `sha256:bab1260…` 保留相同目錄程式碼。
  - [x] 本輪 Overview、Testing schema、Models、System 375px 及無 Token 401 畫面已在 ChatGPT browser tool output 擷取並檢查。新版畫面尚未匯出為 repo 圖檔；匯出限制統一追蹤於 V05。

- [ ] **F07 Sessions 與 Runs**　依類型、元件、DB、時間及狀態查詢；session 詳情列各 run、公開 state／summary。run 詳情列輸入輸出、時間軸、步驟、工具、錯誤、用量和可追溯的版本。

  資料與驗收：以 DB、session type、session ID 取 runs。fork 的 useSessionLoader 只處理 Agent／Team 並轉成 Chat 訊息，F07 應另保留三種 run 的原始類型、run_id 與 workflow.step_results。依實際契約提供查詢；只在已載入資料過濾的欄位標明範圍。測重整直達、跨頁及同名 session。用有綁 DB 的 Ticket Agent、Team 或 Workflow 驗持久化；其他 Agent 依回應標示可否查歷史。[元件建立](../native_workflows.py) · [AgentOS 入口](../app.py)

  - [x] 3.2.1 Runs 的 session 詳情已加入唯讀 compactions。對既有 Workflow session 呼叫 `GET /sessions/{session_id}/compactions` 得到 HTTP 200 與空陣列，已確認 UI 顯示成功空狀態。[3.2.1 驗收證據](agent-ui-verification-evidence.md#agno-321-ui-verification)
  - [x] 2026-11-22 對既有 Workflow session 唯讀比對 `/sessions/{session_id}/runs` 篩選契約：接受狀態為 `CANCELLED`、`COMPLETED`、`ERROR`、`PAUSED`、`PENDING`、`REGENERATED`、`RUNNING`；`FAILED` 會回 400。`created_after`／`created_before` 要求 Unix epoch 秒，ISO 字串會回 422。UI 已加入本地狀態白名單驗證，並把日期欄位轉為 UTC epoch 秒；production image `sha256:813fe12…` 已包含此修正，後續 image 延續該功能。[API 契約](agentos-api-contract.md#f07-session-run-filter-contract-2026-11-22)
  - [x] ChatGPT browser 的 UI 驗收：`FAILED` 被本地攔截並列出支援狀態，沒有加入 URL filter；`ERROR` 成功回空結果並顯示 no matching runs；台北時間 `2026-11-15 16:00–16:10` 轉為 UTC `2026-11-15T08:00:00Z–08:10:00Z` 並查到 1 筆既有 run。以 `not-a-date` 深連結載入時，無效日期被移除並顯示說明。完整結果見[新版驗收證據](agent-ui-verification-evidence.md#agno-321-ui-verification)。
  - [ ] 有 compaction 紀錄時，驗證時間、訊息數、壓縮前後 token、封存旗標與關聯 run ID。以 API 回傳的 metadata 為顯示範圍。

- [ ] **F08 Run 操作**　延續原有聊天執行。新增 Workflow 執行頁顯示輸入契約、work item／情境、是否串流和會啟動的工作；送出後以 run ID 跟進。取消、continue、重試各自依端點能力提供。

  資料與驗收：Run 可能呼叫模型並執行候選測試。只有明確提交才開始；重載或雙擊不能再啟動一次。先建只讀詳情，新增執行操作列為後續階段。

- [ ] **F09 Knowledge／RAG**　可用 knowledge instance、內容清單、來源、索引／處理狀態、metadata、最後更新。若支援檢索，再加查詢與結果來源；元件頁可連回對應 knowledge。

  資料與驗收：核對 Knowledge 設定與原生 content／search 能力。已配置但空、未配置、沒權限各有不同畫面；檢索引用要可回查同一文件。

- [ ] **F10 Memory、Learnings**　兩個分頁，分別顯示使用者記憶與學習紀錄，欄位含可見範圍、摘要、來源與更新時間；session state 放在 F07。

  資料與驗收：本 POC 使用共享 OS key，依 DB 與 user_id 縮小清單只代表資料過濾。單人基線測有資料、空資料、缺憑證。將來若要開放多人，須先有後端綁定的獨立身分，再測以 A 的身分直接查 B 的清單及詳細 ID 均遭拒。名為 Memory／Knowledge 的 Agent 也要依實際設定判定能力。[POC 的認證限制](../README.md#operations-and-limitations)

- [ ] **F11 Traces**　由 run 前往 trace，顯示 span 樹、父子關係、工具或模型、延遲、錯誤與可公開的輸出。外連 Langfuse 時保留相同 trace。

  資料與驗收：分別標示原生 Traces 和 Langfuse OTel。[實驗 runner](../native_experiment_run.py) 對 Agent／Workflow 成功呼叫會記錄 agno_run_id、session_id、trace_id；[一般 demo](../native_demo_run.py) 沒有保存同樣的映射。正例選有確切配對的紀錄，反例用同 session 內兩筆 run；只有 session 或情境相符時，列為「此 session 的相關 traces」，不自動開其中一筆。

- [ ] **F12 Metrics／成本**　既有頁使用 3.2.1 仍提供的 `GET /metrics`，依日期、DB 與可選資料表顯示每日 run／session 數，以及回傳的 token／model 彙整。新增的 AgentOS operational metrics 卡涵蓋 latency、models、runs、sessions、tokens、users；其中 5 個端點目前有資料，users 端點明確回報未配置原因。已依 API `total_runs`／`success_rate` 顯示推算失敗率並驗到 0% 失敗、零 runs 的 N/A、明確的 0 token、缺失 token 欄位時不呈現部分總和，以及隔離 fixture 的 0% success／100% failure；真實 failed run 樣本仍待驗。AgentOS 3.2.1 原始碼確認 `/metrics` 對日日期使用 `>= starting_date`／`<= ending_date`，`/os/metrics/*` 也以兩端 inclusive 的 UTC calendar dates 解析；單日範圍已在 browser 實測。成本欄位未由 3.2.1 API 提供，UI 明確顯示未提供、不估算。[3.2.1 inventory](agentos-api-openapi-3.2.1.md)

  - [x] `/os/metrics/latency|models|runs|sessions|tokens|users` 以唯讀 GET 實查；傳日期區間，支援 DB 的端點另傳所選 `db_id`。本部署 latency／runs／sessions／tokens 各回 8 筆日資料、models 回 1 筆，users 回 503 `User metrics not available: pass a user_directory to AgentOS to enable this feature.`
  - [x] Observability → Metrics 加入六張彼此獨立的 operational metric 卡，每張各有來源、loading／error／Retry；僅呈現白名單化彙總欄位，不顯示個別 user records、不推算 cost。ChatGPT in-app browser 375×844 實測成功資料與 Users 未配置錯誤狀態；新版 image `sha256:8f1269…`，無頁面水平溢位。
  - [x] Image `sha256:c2f78c7…` 新增 Runs failure-rate 欄位，僅在 `total_runs > 0` 且 `success_rate` 是 0–100 的有限數值時以 `100 - success_rate` 計算；0 runs 顯示 `N/A`。ChatGPT browser 375×844 單日 `2026-11-17` 實回 1 run／100% success／0% failure；單日 `2026-11-18` 成功空結果顯示 0 runs／N/A。`GET /metrics` 的 11/17 token summary 明確為 0，保留 0 而不顯示缺值；日期列直接呈現 API 日期字串，預設七日範圍採 browser local calendar。當時尚未檢查日期邊界與失敗／缺欄位 fixtures；日期 inclusive 規則與後續合成 fixture 驗收見本節下一子項。真實失敗 run 和 cost 欄位不可用。首次 Metrics 頁的 DB options 載入顯示 generic `Failed to fetch`，按 Refresh 後 `/config` 資料庫選項成功出現；未將此視為注入斷線測試。
  - [x] 2026-11-22 Docker mock Metrics fixture 刻意省略兩筆 daily rows 的 `token_metrics.total_tokens`，375px ChatGPT browser 顯示 `Incomplete`、不加總 partial total，並逐列標示 `Not returned total`；`/os/metrics/runs` fixture 回 2 runs／0% success，UI 顯示 100% failure。Users fixture 503 仍獨立顯示。此為合成狀態呈現驗收，不是真實失敗 run。日期 inclusive 規則以同版 AgentOS source 的範圍比較與 `_window` 實作確認；見驗收證據。

  資料與驗收：每個指標記錄時間窗、時區、資料範圍、單位及來源。以相同範圍的完整 runs 算失敗率；部分 traces 只能顯示該樣本的延遲。父子 spans 共用用量時僅計一次。runner 的 cost 為 null，保留「未提供」。測零筆、部分資料與真的零成本三種情況。

- [ ] **F13 Evaluations／實驗**　原生 evals 與 POC 的 Langfuse datasets／A/B 各有入口。可按案例比較 A、B、實際輸出、分數、評分理由、版本及 trace。

  資料與驗收：使用 Langfuse dataset run 取得 A/B 結果，依 dataset、item、split、比較維度與對應試次配對，列出不相符的案例／程式／模型版本，缺一側則保留單側結果。Agent 或 Workflow 有回傳才連 Agno run；review-gate 是本機 gate 評估，可以只有實驗 trace。開放的案例輸入與評審答案各自授權，聊天與執行輸入不帶 holdout 答案。[A/B 規劃與現況](langfuse-ab-evaluation.md)
  - [x] 新增 Observability → Evaluations 唯讀頁：`GET /eval-runs` 支援所選 DB、evaluation type、component type／ID、model ID 與分頁；清單可用 `/eval-runs/{id}` 載入詳情，輸入及結果 JSON 預設收合。頁面不提供 eval create／run 動作，也不製造分數。
  - [x] 在本機 AgentOS 3.2.1 對所選 DB 實查 `GET /eval-runs?limit=10&page=1` 為 HTTP 200、0 筆，meta 為 page 1／total_count 0／total_pages 0；ChatGPT in-app browser 顯示成功空狀態、1 頁、Token 遮罩。生產 build／部署 image `sha256:9d41d8585e5e3828a11217bd638589789df10529278eb06539001f8ceb20f245` 已在該頁確認 Filter 為深色 outline。
  - [ ] 目前沒有原生 eval-run 資料，也沒有驗證過的 Langfuse dataset run；因此無法在真實輸出上比對 A／B、評分理由、定義／模型版本、Agno run 與 trace。完成條件仍需一次經授權且可重查的實驗結果；不以 JSON fixture 假扮已執行結果。

- [ ] **F14 Approvals／HITL**　列待處理、已處理、發起者、動作、依據與關聯 run。Agno 原生可續跑的 paused run 與 POC 業務審查各有狀態文字。

  資料與驗收：① POC 的 `READY_FOR_HUMAN_REVIEW`、`released=false` 為唯讀業務結果。② 中央 Approvals 在這份 3.2.1 快照只註冊 disabled 路由，需有支援的 OS 級資料庫配置，再確認實際核准資源及決議契約。③ v3 Workflow HITL 使用 `HumanReview`。原生 paused run 依 Agent、Team 或 Workflow 各自的 `continue` request schema 補交所需資料，可能沒有中央 approval ID。P3 對後兩種操作分別驗能力、身分、最新狀態與結果。[3.2.1 inventory](agentos-api-openapi-3.2.1.md) · [v3 升級紀錄](agno-3.2.1-upgrade.md#官方升級依據與已知-breaking-changes)
  - [x] System 加入唯讀 `GET /approvals` 狀態檢查，不讀取 approval records。使用者在 image `336c9a8…` 的 ChatGPT browser 輸入 Token 後 UI 顯示 HTTP 503；image `3e55f72…` 的無 Token 狀態顯示 HTTP 401／需驗證；2026-11-22 production image `0052fa5430b7…` 授權覆驗仍為 503。沒有中央 approval records 清單，不顯示虛構的空列表；單路由 Recheck 已單獨驗過。

- [ ] **F15 Schedules**　可讀取時展示目標、週期、時區、啟用狀態、最近／下次執行與 run history。從某筆歷史執行連到 F07。

  資料與驗收：3.2.1 快照只列出 disabled `/schedules` 路由。須先核對 scheduler 與 DB 配置，再以實際回應確認排程時區、歷史及執行狀態。
  - [x] System 加入唯讀 `GET /schedules` 狀態檢查，不載入 schedule records。使用者在 image `336c9a8…` 的 ChatGPT browser 輸入 Token 後 UI 顯示 HTTP 503；image `3e55f72…` 的無 Token 狀態顯示 HTTP 401；2026-11-22 production image `0052fa5430b7…` 授權覆驗仍為 503。排程資料與時區尚無法從此部署讀取。

- [ ] **F16 系統與整合**　部署版本、已註冊元件、DB 顯示名稱、可用模型、MCP／介面、gateway、Backstage、報告、Langfuse 連結；每個功能列支援狀態、依據與最後檢查時間。

  資料與驗收：讀原生 `/health`、`/info`、`/config`、Factory revision 和白名單整合設定。3.2.1 的模型摘要來自 `/config.available_models`，舊版相容才查 `/models`。外部網址用宿主機可開啟的地址，本 POC gateway 的 `/report` 可作報告入口。[3.2.1 驗收證據](agent-ui-verification-evidence.md#agno-321-ui-verification) · [服務與報告](../README.md)
  - [x] image `sha256:89cd59f…` 提供 Langfuse app／health、Gateway health／PAY-482 report、Backstage Catalog 直接連結。image `sha256:3e55f72…` 另由 Agent UI server 對 Docker Compose 網路上的 Langfuse `/api/public/health`、Gateway `/health`、Backstage `/healthcheck` 做唯讀 GET；UI 顯示各 HTTP status 與最後檢查時間，不讀取回應本文，並有 Refresh all／Retry。較新 image `0052fa5430b7…` 保留這些能力並包含 Team state 修正。
  - [x] ChatGPT in-app browser 的桌面覆驗顯示三項外部端點均為 HTTP 200。這些狀態只代表 Agent UI 容器到健康端點可達；Langfuse project／trace 關聯未驗，Backstage Catalog Graph 由獨立 Guest 瀏覽器驗收，Backstage Catalog API 未登入時回 401。
  - [x] 歷史 System checkpoint：使用者在 ChatGPT browser 輸入 Token 後，System 顯示 health OK、26 Agents／3 Teams／2 Workflows、Factory revision、1 session DB、1 model、0 interfaces。`/approvals`、`/schedules`、`/components`、`/queue`、`/service-accounts` 為 503，`/registry` 為 200；Token 遮罩。Image `336c9a8…` 完成授權資料驗收，image `3e55f72…` 加入單路由 Recheck；image `0052fa…` 的授權 Registry records 驗收見下方 F17／V04，後續部署與本輪覆驗見 V04。
  - [x] 2026-11-22 System Explorer 已把 Retry 縮小至來源群組：Deployment 只重查 health/info，Factory revision 只重查 revision，config/model cards 只重查 `/config`（缺 model list 時才 fallback `/models`）；成功資料在其他來源錯誤時保留，Deployment 會顯示 `/info` 失敗。DB name 若與 ID 相同會說明「顯示名稱與 DB ID 相同」，不重複列出相同字串。前一 production image `sha256:813fe12…` 含此功能；現行 image `sha256:335cab6…` 已部署。ChatGPT browser 的 dev UI 驗到 health／Registry 資料及 Approvals 單卡 Retry；mock 已驗可重試錯誤，真實外部 API 故障隔離仍待驗。
  - [x] 2026-11-22 以獨立 Docker network 讓 Langfuse／Gateway／Backstage service names 不可解析，AgentOS 則指向隔離 mock。ChatGPT in-app browser 的 System 顯示三個外部項目皆 `UNREACHABLE`／整卡 `ERROR`；Deployment、Registered components、Factory revision、Session storage、Registry 等 AgentOS 卡仍維持已載入。按外部 Retry 後三個項目的檢查時間更新、失敗仍局部保留，其他 AgentOS 資料不重載或清除。只讀故障注入未停止 production 或外部服務；截圖在 browser tool output，未擷取整個電腦。細節見[驗收證據](agent-ui-verification-evidence.md#2026-11-22-f16-isolated-docker-network-outage-check)。
  - [ ] F16 尚待核對 Langfuse trace 與 AgentOS run 的關聯。DB 顯示名稱已由 `/config.session.dbs[].domain_config.display_name` 投影到 System；目前唯一 DB 的 `display_name` 恰與 ID 相同。Backstage Graph 已以 `system:default/ai-factory` 為根顯示實際 Catalog nodes／relations。Langfuse project API 有 1 個 project；2026-11-22 最新唯讀觀察為 14,763 traces，10 筆抽樣均未見 AgentOS run/session 關聯欄位。外部健康／trace 數量不等於配對驗收。限制見[驗收證據](agent-ui-verification-evidence.md)。

- [x] 2026-11-22 用 production image ID `sha256:0052fa5430b7eed45fc2d78eb0e29f04f71c7cb76c57252fb28eb7927ade7967` 於 ChatGPT browser 覆驗授權 System：health OK、Agno 3.2.1、26 Agents／3 Teams／2 Workflows、1 session DB、1 model、0 interfaces；Approvals／Schedules／Components／Queue／Service Accounts 為 503，Registry 200／69 records。Token 遮罩；Langfuse／Gateway／Backstage 仍僅 health 200，不推論專案或 trace 關聯。

- [ ] **F17 進階能力盤點**　將目前版本其餘 OpenAPI tags 分配到上列頁面。例如元件 registry／Studio 版本資料、模型／資料庫管理、服務帳號與權限、其他介面或遠端元件。SDK 特性如 guardrails、hooks、重試或 reasoning，放在所屬元件設定或公開事件。

  資料與驗收：每個未納入首版的家族在系統頁寫明「需配置」「版本未提供」「權限受限」或「本期只讀」。未透過 API 暴露的 Python 設定需由後端明確選欄輸出。
  - [x] System 加入 `/components`、`/queue`、`/service-accounts`、`/registry` 的唯讀 HTTP status checks；不讀取 records 或 credentials。image `3e55f72…` 無 Token 時六路由均顯示 401；授權的 production UI `0052fa5430b7…` 對前五路由回 503、Registry 回 200。新 image 的 Approvals Recheck 只更新該列時間，另外五列時間不變，驗證單一路由重查相互獨立。
  - [x] 新增 System → AgentOS registry records 唯讀頁：`GET /registry`、resource type／name 篩選、分頁、URL query state、Retry 與白名單 metadata 摘要；不提供寫入或 DB 篩選。已授權 API 與 production browser 都驗到 69 筆（26 agents、3 teams、2 workflows、27 tools、9 functions、1 model、1 db）；UI 69 筆／7 頁，page 2 載入不同清單、`team` 3 筆、`Governance` 1 筆、Clear 還原 69／7。畫面不保存 Registry names／IDs。
  - [x] 3.2.1 live OpenAPI 已逐 operation 建立 94 paths／135 operations／164 schemas inventory，對應 21 個標準 tags 與 5 個無 tag 的 Factory extension operations；各 tag family 的路由／設定／認證／資料狀態見 [API 契約 crosswalk](agentos-api-contract.md#321-live-tag-family-routeconfigauthdata-crosswalk-2026-11-22)。
  - [x] 已對 FileSystem 4 個 GET、Media 1 個 GET 做授權取樣；`factory-09` 沒有 FileSystem，四路由均回 404；Media storage 未配置，回 503。未指定 filesystem scope 的 `/filesystem/files` 回 200／空陣列，不可當成已配置空資料。結果記於[API 契約](agentos-api-contract.md#321-live-tag-family-routeconfigauthdata-crosswalk-2026-11-22)。
  - [x] 2026-11-22 bounded GET sweep 執行完成：70 個 OpenAPI GET 中抽查 62 個，狀態為 40×200、13×404、3×422、6×503；精確補查既有 Agent／Team／Workflow session、runs、previews、detail、checkpoints 及 Sessions page 1／2／999。此項表示有界取樣已執行，不表示 operation-level audit 全面完成；見[API 契約](agentos-api-contract.md#bounded-live-get-sweep-2026-11-22)。
  - [ ] 完整 runtime 取樣仍缺 8 個可能回傳 file／content／media bytes 的 GET、其餘 query／DB／pagination 邊界、非空 Trace／Eval detail 與已配置 Knowledge／FileSystem／Media fixture。Generic 404／422 不推論端點停用或資料不存在；管理操作沒有送出。這些缺口仍由 P0.3 追蹤。


## Agno 3.2.1 API 契約

- [x] 已保存 3.2.1 Docker 部署的 [OpenAPI 清單](agentos-api-openapi-3.2.1.md)。以下依功能摘錄與本計畫相關的路由。OpenAPI 的 security 與 schema 欄位是契約宣告，實際授權、配置與資料狀態另見 [3.2.1 HTTP 驗證](agentos-api-contract.md#321-live-contract-checks)。
- [x] 歷史比較資料仍可查閱。2.9.0 離線 probe 為 72 paths，後續 2.9.0 Docker 快照為 75 paths／112 operations。[歷史 API 快照](agentos-api-contract.md#historical-openapi-operation-inventory-agno-290)

| 功能家族 | 3.2.1 部署契約摘錄 | 接手時如何使用 |
| --- | --- | --- |
| 元件、模型與系統 | `GET /agents`、`/teams`、`/workflows` 及其詳情，`/registry`、`/health`、`/info`、`/config` | 由原生步驟與 Factory 同一部署定義呈現 Workflow。缺少可對齊的節點識別時分開展示。模型由 `/config.available_models` 提供，已實測 `/models` 回 404。 |
| 執行歷程 | `GET /sessions`、`/sessions/{session_id}/runs`、`/sessions/{session_id}/runs/{run_id}`、`/sessions/{session_id}/compactions`。各元件另有 runs 與執行操作路由。 | Sessions 依 `type`、`component_id`、`db_id` 及 `page`／`limit` 查詢。Session runs 契約列出 `status`、`limit`、`before_run_index`、`after_run_index`。實作分頁前核對邊界及排序。Compactions 已驗 HTTP 200 空資料。 |
| 資料 | `GET /memories`、`/memory_topics`、`/user_memory_stats`、`/learnings`、`/learnings/users`、`/knowledge/config`、`/knowledge/content`，另有 `POST /knowledge/search` | 核對 DB、Knowledge instance、分頁及實際資料。Knowledge config/content 宣告 `db_id`／`knowledge_id`。Search 契約宣告 request body，使用者送出查詢時才呼叫。匯入與重建索引走各自操作。 |
| 觀測與實驗 | `GET /traces`、`/traces/{trace_id}`、`/traces/filter-schema`、`/trace_session_stats`、`/metrics`、`/os/metrics/*`、`/eval-runs`，另有 `POST /traces/search` | `/traces` 可依 `run_id`／`session_id`、時間與 `db_id` 查詢。原生 Trace 與 Langfuse 分別核對。既有 `/metrics` 用 `starting_date`／`ending_date` 查日彙總。Eval 清單按契約支援元件、模型、類型與分頁。 |
| 營運與管理 | `/approvals`、`/schedules`、`/components`、`/service-accounts` 為 disabled 路由。DB migration 有獨立 `POST /databases/…/migrate`。 | 依部署的 OS DB 及 scheduler 配置判斷能力。實際錯誤與權限另驗；DB 遷移使用既有維運流程。 |
| Factory 與外部資料 | POC 自訂 `GET /factory/revision` 及 `/factory/workflows/{id}`、`/factory/agents/{id}`、`/factory/teams/{id}` | Factory 路由從已部署 registry 讀取並套用白名單與認證。Langfuse、工單與報告依 POC 各自的整合來源確認。 |

## 實作順序與交付條件

### P0　讓這個 POC 的能力與建置可以重現

- [x] **P0.1 保存 2.9.0 歷史起跑點。** Compose project 為 `agno-factory-local`，Agent UI／AgentOS／Langfuse 的宿主機 ports 為 3000／7777／3001。起跑時所有長駐服務已退出。舊 image 中 Agno 是 2.9.0，Langfuse Python 套件未安裝。當時的 UI commit、registry revision、image ID 與檢查命令見[實作紀錄](agent-ui-implementation-log.md#2026-11-21-起跑基線)。
- [x] **P0.2 把 UI 修改留在 POC，固定已驗版本。** [Dockerfile.ui](../Dockerfile.ui) 固定 fork commit `817a009b3d7e407b17b48872f5bbf1c5055b5955`、安裝 frozen lockfile 並套用 POC patch。AgentOS 由 [requirements.txt](../requirements.txt) 和 [requirements.lock](../requirements.lock) 固定為 3.2.1。兩個 3.2.1 環境使用的 image 均已成功建置。預設 Compose 使用公開 AgentOS image，本機 build 需加上 [build overlay](../docker-compose.build.yml)。日常 UI 迭代另有 [bind-mounted dev overlay](../docker-compose.ui-dev.yml)，掛載工作樹 `src/` 並以 Next dev server 熱更新；此流程 typecheck 通過，但 dev log 出現 Watchpack `ENOMEM` 掃描警告，需留意本機資源下的監看穩定性。最後驗收 production build 已於 2026-11-23 完成，部署 image `sha256:335cab6…`。[實作紀錄](agent-ui-implementation-log.md)
- [ ] **P0.3 建立部署契約與逐頁驗收對照（operation／schema／tag mapping 已完成，runtime sampling 擴充但仍部分完成）。**
  - [x] 從運行中的 AgentOS 3.2.1 擷取 live OpenAPI，共 94 paths／135 operations；記錄方法、參數、schema refs 與安全宣告。[3.2.1 inventory](agentos-api-openapi-3.2.1.md)
  - [x] 補上 `/info`、`/config.available_models`、`/models` 404、Factory revision 及 Workflow session compactions 的執行結果。[API 契約與 HTTP 驗證](agentos-api-contract.md#321-live-contract-checks)
  - [x] 對已操作的唯讀路徑記錄實際狀態與資料：Overview 的 health/info/config/revision/sessions、Factory catalog、Tools／Skills／Models、三類 Sessions／Runs、Memory／Learnings／Knowledge、Traces／Metrics、compactions，以及 Factory detail。已在各 checkpoint 註明路由存在、實際授權結果、已配置情況與回傳是否有資料；本輪補驗無 Token 下 System 保護來源的 401 和 Overview 三來源 Retry。
  - [x] 2026-11-22 targeted read-only GET audit 補記 `/approvals`、`/components`、`/queue`、`/schedules`、`/service-accounts` 的授權後 503，以及無 Authorization 時 401；同時核對 Registry pagination、empty eval/trace/memory/learnings、Knowledge 無 `db_id` 時 503／選定 DB 時 404、filter schemas 與 metrics status。分組結果與實際筆數見[3.2.1 API 契約](agentos-api-contract.md#321-targeted-read-only-get-audit-2026-11-22)。這仍不是 135 operations 的完整逐項 runtime 驗證。
  - [x] 2026-11-22 supplemental safe GET audit 覆蓋 Agents／Teams／Workflows list/detail、三類 session/detail/run/preview、Agent／Team checkpoint 與 snapshot、三類 compactions、metrics refresh status、Evals 空清單及未知 detail 404。Workflow run sample 有 6 step results／10 executor runs；Agent／Team／Workflow compactions 都是成功空集合。只保存 status／aggregate counts／欄位形狀，不記錄本機 record IDs 或內容。[補充 runtime samples](agentos-api-contract.md#additional-authenticated-read-only-runtime-samples-2026-11-22)
  - [x] 已完成 OpenAPI operation／schema／tag-family 靜態 mapping：94 paths／135 operations、164 schemas、21 個標準 tags 及 5 個無 tag 的 Factory extension operations；每項有 method、參數、schema refs、安全宣告與功能家族對應。[API 契約 crosswalk](agentos-api-contract.md#321-live-tag-family-routeconfigauthdata-crosswalk-2026-11-22)
  - [x] 2026-11-22 另以唯讀 AgentOS request 驗證 F07 run filter：七種合法 status、`FAILED` 的 400，以及日期參數須為 epoch seconds；對應 UI 驗證與契約已加入 [F07 contract](agentos-api-contract.md#f07-session-run-filter-contract-2026-11-22)。
  - [ ] Runtime 認證、DB、分頁與錯誤抽查尚未逐 operation 完成。2026-11-22 bounded sweep 對 70 個 OpenAPI GET 中 62 個作授權取樣；8 個可能回傳 content/file/media bytes 的路由跳過。掃描結果與 generic unknown IDs／cursor 的限制見[API 契約](agentos-api-contract.md#bounded-live-get-sweep-2026-11-22)。針對既有 Agent／Workflow session 的 list、runs、preview、detail 與 checkpoint 做了精確補查；另對 Sessions、Memory、Learnings、Evals、Traces、Registry 用 `limit=1` 抽查 page 1／2／999。仍缺已配置 Knowledge source/files、非空 Trace／Eval detail，以及完整 GET surface 的 query／DB／pagination 組合；逐頁仍區分「路由存在／已配置／允許讀取／有資料」。啟動頁只探測白名單內的輕量讀取；知識搜尋、指標重算、評估與執行由使用者明確操作。
- [ ] **P0.4 保護資料來源（部分驗收）。** 單人 POC 第一版沿用記憶體中的 runtime Token。已移除 Compose／Dockerfile 公開 key 注入，掃描確認靜態產物不含 `.env` OS key；本機 Agent UI 的已授權 Token 輸入、遮罩顯示、重載清除與無 Token 401 已驗。Same-origin proxy 使用 server-only `AGENTOS_URL`；目前 production image `sha256:335cab6…` 未含 proxy Token fallback，Docker 內 `/api/agentos/health` 回 200、無授權 `/api/agentos/config` 回 401。dev 驗收期間的臨時 auth fallback 與容器已移除。Endpoint 切換 abort／清除快取與 synthetic stream 延遲 callback 行為已驗；Overview DB A→B 舊回應隔離也以 mock 驗收。這些不證明真實 AgentOS／模型 stream 的 TCP 中止或 request-log UI／紀錄隔離，仍待驗。Langfuse 私鑰只在後端使用。
- [x] **P0.4 前一 production checkpoint 覆驗。** Docker CLI 確認當時的 `factory-agent-ui` 執行 image ID `sha256:0052fa5430b7eed45fc2d78eb0e29f04f71c7cb76c57252fb28eb7927ade7967`；ChatGPT browser 顯示授權 Registry 結果及 3 Teams，包含 `setTeams(teams)` 初始化修正。Token 仍只在記憶體中並以遮罩顯示。該 image 先後由 `sha256:337b6ded…`、`sha256:c2f78c7…` 取代；真實 stream abort 與 request-log 隔離仍未完成。
- [x] **P0.5 移植三條 Factory 路由。** 局部適配 [app.py](../app.py)，保留既有 work-item middleware、Langfuse 和 Reviewer 流程。以 registry.load() 已選定部署快照為準；Docker 驗證無 Token 401、已知 ID 200、未知 ID 404、revision 一致及白名單回應未含環境值、DSN、憑證標記或內部路徑。結果見[實作驗證紀錄](agent-ui-implementation-log.md)。

### P1　先交付一條能走完的查看路徑

P1 的 Workflow／Agent／Team 故事與 Runs 窄版截圖是 2.9.0 的驗收紀錄。3.2.1 升級時複驗了 Workflow Run 與 compactions 空狀態。跨元件與 DB 的 Runs 深連結反例、網路復原及新版窄版仍有待辦。[驗收證據](agent-ui-verification-evidence.md)

- [x] **P1.1 系統與殼層及詳情錯誤降級。** 第一輪 UI 保留 fork 的 Chat、Agents、Teams、Workflows。WorkflowExplorer 將原生清單與 Factory revision 分開請求，先呈現原生 Workflow 再補 Factory 設計；Agent／Team 有兩種原始 JSON disclosure；Docker production build 與瀏覽器正常路徑通過。使用本機合成 fixture 分別注入 Factory definition 404 與 AgentOS runtime detail 404；成功的另一來源仍可見，點 Retry 只重送失敗來源。這驗證 UI 局部降級，不代表真實部署對未知 ID 的 runtime response。[實作紀錄](agent-ui-implementation-log.md)
- [x] **P1.2 第一個驗收故事。** 從 Software Delivery → Parallel Verification → Testing Agent 詳情，查看角色、完整 ID、模型、runtime tools、Skills 與 instructions；第二條從 Continuous Improvement → Observability Team → 成員 Agent 詳情，查看 Team mode、members、runtime tools 與兩種 JSON disclosure。26 Agents、3 Teams、2 Workflows 已由 Docker UI 載入；截圖與窄版數據見[驗收證據](agent-ui-verification-evidence.md)。
- [ ] **P1.3 接通 F07（首輪三類唯讀 Runs、DB selector、filter 與基本深連結已驗，完整 F07 仍進行中）。** Docker UI 的 Runs 工作區支援 Agent／Team／Workflow 三種 session type，按類型載入元件、Sessions 分頁、該 session 的 Runs 與單筆 run detail。AgentOS `/config.session.dbs[].db_id` 與元件回應的 `db_id` 供 Database selector；`AgentOS default` 會移除 URL filter，具名 DB 經 `db_id` 過濾。375px 驗到 7 筆 Agent sessions（抽樣 run `COMPLETED`、6 messages、2 tool calls）、Observability Team 1 筆 session／5 筆 runs，以及 Software Delivery Workflow 13 筆 sessions／每頁 5 筆／共 3 頁；翻頁仍可載入 Runs。Governance Team 的 0 筆成功回應顯示空狀態；無 Token 顯示 401／Retry。Runs URL 已含 `view`、type、component、page、session、run；Agent page 1／page 2 重載並重新授權後均還原。Per-view query allowlist 讓 Runs 切 Overview 清除舊 Runs filters、保留 Overview DB，切 System 後 URL 固定為 `?view=system`。不存在 Session 顯示 not-found 且可改選；不存在 Run 顯示 404／Retry。Browser 已驗 `FAILED` 本地攔截、`ERROR` 成功空結果、有效台北日期範圍、無效日期清理及 socket drop 後 Retry。隔離 fixture 驗證 DB A 的深連結不載入只存在 DB B 的 session，source 修正並已部署至 2026-11-23 的 `sha256:335cab6…`。同日 production browser 帶 `db_id` 深連結載入既有 Workflow session/run，URL 和 Database selector 保留指定 DB。API 另以既有 Agent session 驗 `run_index` cursor indices 2→1→0 無缺漏／重複。仍缺真實正向 Run-to-Trace 關聯與非空 compaction。詳見[驗收證據](agent-ui-verification-evidence.md#f07-runs-isolated-recovery-and-deep-links)及[API 契約](agentos-api-contract.md#2026-11-23-session-run-cursor-sample)。不要把 Workflow 執行誤作 Agent Chat。[fork 的 Sessions API](https://github.com/CletusLee/agent-ui/blob/817a009b3d7e407b17b48872f5bbf1c5055b5955/src/api/os.ts)

### P2　資料、觀測與實驗

本節的筆數與畫面來自 2.9.0 驗收，另註明的 3.2.1 項目有新版證據。重新取樣時依 [3.2.1 inventory](agentos-api-openapi-3.2.1.md) 的參數與 schema 判讀結果。

- [ ] **P2.1 上線 F09／F10（唯讀 Data Explorer 與未配置狀態已部署，真實內容資料仍未全驗）。** 選定 DB 的 `/memories` 與 `/learnings` 均為 200、0 items，UI 會顯示成功空狀態；`/knowledge/config?db_id=...` 回 404。Data Explorer checkpoint image `sha256:e05479e55c3f173d60f7913e1b79d44245daa7fddc0a74f95a256e5d02c4a446` 已實際部署；後續 image `sha256:25d2e4b...` 包含相同 Data Explorer 及 Observability 改動。只讀 Data view 已加入 Memory／Learnings／Knowledge tabs、DB selector、`view=data`／`data_type`／`data_page`／`db_id` URL state、欄位卡及完整 record disclosure；375px／1280px Docker build、部署、reload 還原已驗。375px 目前另驗 `window.innerWidth=375` 且 document `scrollWidth=375`，Data Explorer 無水平溢位。尚須以有資料的 Memory／Learning 和已配置 Knowledge 驗證欄位、分頁、內容來源及搜尋結果；P2.1 因此維持未完成。單人 POC 在系統頁標明共享 key 的可見範圍；未配置獨立使用者授權前，跨身分隔離列為「不適用於此部署」。
  - [x] 2.9.0 歷史驗收已核對 Knowledge content、search 與 source listing。3.2.1 清單也已收錄其路由、參數及 schema refs；配置後的資料驗收見下方待辦。
  - [x] 即使 config 404，保留 Knowledge 子頁入口；Configuration 顯示未配置說明，Content 以 `/knowledge/content` 的 404 顯示無可用 Knowledge content endpoint，Search 的唯讀 POST 也顯示未配置說明與 Retry，沒有讓 config 失敗隱藏其他功能。
  - [ ] Knowledge 已配置時列出內容、處理狀態、來源 metadata 與分頁；載入失敗和成功空清單需分開呈現。
  - [x] 加入唯讀 Knowledge search 與結果來源／metadata；UI 標明唯讀 `POST /knowledge/search`，查詢文字只留在頁面記憶體而不寫進 URL。已在 375px 實送唯讀查詢並驗證未配置狀態；因本 DB 沒有 Knowledge instance，尚不能用真實搜尋結果驗證來源／metadata 呈現。
  - [ ] 使用至少一筆真實 Memory／Learning 和一個已配置 Knowledge instance 驗證資料欄位、分頁、檢索來源；無此 fixture 時記錄明確限制，不偽造結果。
- [ ] **P2.2 上線 F11／F12（唯讀 Observability Explorer 已部署，真實 Trace detail 待資料）。** 既有頁使用 `/traces`、`/traces/{trace_id}`、`/trace_session_stats` 與 `/metrics`。Run→Trace 以精確 `run_id` 關聯。Trace detail 顯示來源、Trace ID、時間、duration、span hierarchy、錯誤及公開的 input/output。Metrics 標示時間窗與資料範圍，缺成本欄位時顯示未提供。
  - [x] 2.9.0 歷史驗收已核對 Trace summary/detail/node、分頁、Session stats 及 daily Metrics schema。3.2.1 inventory 列出既有路由及 `/os/metrics/*`，依實際 response 核對新指標。
  - [x] 2.9.0 歷史查詢中，DB Traces 與 trace session stats 各 200／0 筆。2026-11-15 至 2026-11-21 Metrics 200／2 日資料。
  - [x] 已完成 source slice：新增 Trace 清單、run/session/status filter、分頁、span tree detail、trace_id 深連結，以及每日 Agent／Team／Workflow runs、sessions、tokens 摘要和日期範圍查詢；依 GET schema 呈現 API 未提供的成本為不估算。
  - [x] Docker patch/build/deploy；桌面與 375px 瀏覽器載入新版 UI。Traces 與 trace session stats 均成功回 0 筆；Metrics 查到 2 日資料（35 runs、31 sessions，API token total 989,821）。在 375px 驗 `document.documentElement.scrollWidth === window.innerWidth === 375`，兩頁均沒有水平溢位。
  - [x] 以 `trace_id=codex-verification-missing-trace` 開啟未知 Trace 深連結，UI 顯示 `Trace was not found in the selected database.` 與 Retry；證據：[Trace not found](screenshots/observability-trace-not-found-desktop.jpg)。
  - [x] Fork source 已加入可選資料表名稱欄位，Apply 後將 `metrics_table` 保存在 URL 並傳入唯讀 `GET /metrics?table=`；留白表示 AgentOS 預設。API 要求有 table 時必須帶 `db_id`，UI 會先顯示清楚錯誤並停止無效請求。
  - [x] Fork source 已新增共用的 Database selector，從 AgentOS session DB options 載入選項並呈現 loading／unavailable 狀態；切換 DB 會清除 trace detail 和與舊 DB 綁定的 table name，並將 `db_id` 更新到 URL。
  - [x] Fork source 已在 selected run detail 加入「View traces for this run」，以精確 `run_id` 導向 Observability Traces、保留目前 `db_id`、重設 trace page 並清除舊 session/status/detail filter。
  - [x] 2.9.0 的 Run→Trace 導覽已於 Docker 驗收。從實際 Workflow run 點擊可到 Observability Traces，保留精確 `trace_run_id` 與 `db_id`，頁面收到成功的 0 筆結果。[Workflow Run 按鈕](screenshots/workflow-run-traces-link.jpg) · [精確 Run 篩選結果](screenshots/observability-run-trace-filter-empty-desktop.jpg)
  - [x] Metrics table／DB 瀏覽器驗收完成：選具名 DB 及 `agno_metrics` 後 `/metrics` 成功回 2 日資料、35 runs、31 sessions、989,821 tokens；URL 可還原篩選。只選 AgentOS default 且輸入 table 時會先顯示提示、不送無效 request。375px 無水平溢位；畫面：[Metrics 與資料表](screenshots/observability-metrics-table-filter-desktop.jpg)、[無具名 DB 驗證](screenshots/observability-metrics-table-requires-db-desktop.jpg)。
  - [x] 以已選 DB 查詢不存在的 table `codex_missing_table_verification`，AgentOS 回 500；UI 顯示 `AgentOS returned 500 Internal Server Error` 與 Retry。此 API 對不存在 table 實際回 500，驗收不假設為 404。畫面：[Metrics unknown table error](screenshots/observability-metrics-unknown-table-error-desktop.jpg)。
  - [ ] AgentOS 原生 `/traces` 與 trace session stats 均回成功空集合；另有 Langfuse project traces，但抽樣資料沒有 AgentOS run/session correlation。待有可追查的原生 Trace 或具明確映射的 Langfuse trace 後驗證 detail/span tree 與 Run→Trace 正向關聯。
  - [x] 依 live OpenAPI 確認六個 `/os/metrics/*` operation，實查 5 個成功資料端點及 users 未配置的 503，並已整合至 Observability Metrics UI。Image `sha256:c2f78c7…` 的 `/os/metrics/runs` 單日 1 run／100% success 顯示 0% failure；零 runs 顯示 0 與 `N/A` failure。`/metrics` 單日有 1 row、0 tokens，另一日期為空資料。2026-11-22 mock 已驗 2 runs／0% success 的 failure-rate 呈現及缺失 `total_tokens` 欄位時不估算。同版 AgentOS source 顯示兩種 Metrics API 的 date endpoints 為 inclusive calendar days；真實失敗 run 與其他 timezone 語義仍待驗。[驗收證據](agent-ui-verification-evidence.md#agno-321-ui-verification)
- [ ] **P2.3 上線 F13。** 原生 eval-run 用自己的類型及結果。Factory A/B 使用 [案例](../evals)、[runner](../native_experiment_run.py) 和 [實驗交接](langfuse-ab-evaluation.md)。公開的 fixture 與已執行 dataset run 分開；同一案例能依 variant、版本、run 與 trace 比對。Langfuse 尚無已驗證結果時顯示現況。
  - [x] 原生 Evals 列表／篩選／分頁／詳情已接到 AgentOS 3.2.1；live GET 成功空集合與 UI 狀態已驗。這不驗證任何寫入 operation。
  - [ ] Langfuse API 有 1 project；2026-11-22 最新唯讀觀察為 14,763 traces，但 `/api/public/datasets` 回 200／0 datasets；10 筆 trace detail 抽樣未見 AgentOS run/session 關聯欄位。沒有可驗的已執行 A/B dataset run、score 或 AgentOS run／trace 關聯。本輪沒有啟動新的模型 run。
- [x] **P2.4 完成覆蓋盤點。** 已核對模型、工具、Skills、DB、介面與整合的頁面歸屬，21 個唯一標準 OpenAPI tags 與 5 個 POC Factory extension operations 均有對照。Tag family 狀態分為可讀得資料、成功空集合、未配置、只確認路由及 disabled 503；逐 operation 的完整 runtime query／DB／pagination sampling 仍由 P0.3 追蹤。Langfuse trace→run 關聯與外部 outage isolation 是 F16／V04b 的驗收缺口，不屬於覆蓋盤點，見下方續列；Backstage Catalog Graph 已另列驗收結果。
  - [x] F16 System Explorer 已在 Docker 的 Agno 3.2.1 環境完成桌面覆驗。顯示 health、runtime 版本、元件數、session DB、模型摘要、interfaces、Factory revision、六個管理路由的 HTTP status，以及三個外部健康端點狀態與時間。無 Token 時管理路由為 401；使用者輸入 Token 後前五個 management routes 為 503、Registry 為 200；外部探測為 200。[3.2.1 驗收證據](agent-ui-verification-evidence.md#agno-321-ui-verification)
  - [x] F17 Registry 已由單純狀態探測擴充成只讀清單；production image `sha256:0052fa5430b7eed45fc2d78eb0e29f04f71c7cb76c57252fb28eb7927ade7967` 的 ChatGPT browser 驗收讀到 69 筆／7 頁，翻至第 2 頁可見不同資料；`team` 篩選為 3 筆、`Governance` 名稱搜尋為 1 筆，Clear 還原 69 筆／7 頁。畫面只顯示白名單摘要，未保存 registry names／IDs。
  - [x] 從 live OpenAPI inventory 抽出 21 個唯一標準 tag，均在本節有對應列；另將 5 個無 tag 的 POC Factory extension operation 獨立列出。以 tag family 統計目前狀態：8 類已讀得資料、4 類成功但空、1 類未配置、3 類只確認路由、5 類回 disabled 503。Sessions、Metrics 等 family 內含不同狀態的 operations；此統計是能力盤點，不等同 135 個 operations 全部完成 runtime 驗收。
  - [x] 前一 production image `sha256:0052fa…` 的 ChatGPT browser 已完成授權 Registry records／filter／pagination 驗收；本輪 image `sha256:c2f78c7…` 已部署並在同一 ChatGPT browser 覆驗 Overview pending-source、Agents／Teams model search、Metrics 與 System。Registry 程式碼未在本輪變更；Docker CLI 確認目前 `factory-agent-ui` running 並使用新 image ID。
- [x] 2026-11-22 checkpoint image `sha256:c2f78c7…` 的 System／Registry 桌面與 375px 窄版已由 ChatGPT browser screenshot API 擷取及目視檢查；新部署 image 的窄版覆驗仍開放，截圖不擷取整個電腦桌面。
  - [x] 新版截圖另存 repo 的限制統一追蹤於 V05；目前 Browser screenshot API 只有工具輸出，沒有受支援方式把 image bytes 寫入 repo。舊的 [桌面截圖](screenshots/system-explorer-desktop.jpg) 屬於 2.9.0。
  - [x] 較早 image `sha256:8f1269…` 以實際 375×844 viewport 驗 System Explorer：health/runtime 資料可讀；清除 Token 後 config、catalog、session storage、models、interfaces 各自回 401／Retry，來源狀態分開呈現。主內容 client／scroll 寬 334px，document/body 寬 375px，無水平溢位；image `sha256:4f57e9…` 加入 sidebar 鍵盤行為；前一 image `sha256:bab1260…` 保留該行為並增加 endpoint 隔離；image `sha256:7809386…` 延續這些行為。這些是早期 image 驗收，不代表目前 image 的窄版覆驗。
  - [x] 唯讀 GET `http://127.0.0.1:3001/api/public/health` 回 200；這只證明本機 Langfuse health endpoint 可回應，不代表已配對 project、AgentOS OTel 設定或 trace 映射。
  - [x] 2026-11-22 啟動本機 `agno-gateway` 與 Backstage，並啟動 Langfuse worker（web 與資料相依服務已運行）。Gateway `/health` 回 200；`/report` 回 200，標題為「PAY-482 · Workflow 執行報告」、報告日期 2026-11-14。Backstage Guest Catalog 顯示 45 components（26 Agents、3 Teams、2 Workflows、14 Skills）；瀏覽器畫面已截取於 tool output。AgentOS 日誌顯示 `Langfuse OTel tracing enabled`，Langfuse public health 回 200／3.227.1。這些結果只證明連線、報告存在與 exporter 初始化。
  - [x] image `sha256:3e55f72…` 已部署；System Explorer 保留五個 host-local 外部連結，新增服務端唯讀 GET 健康探測及每項最後檢查時間。ChatGPT browser tool output 的新版桌面畫面可見 Langfuse、Gateway、Backstage 均為 HTTP 200。截圖尚無支援方式寫成 repo 檔案。
  - [x] 較早 Docker inspect 確認 Agent UI／AgentOS 均 running；容器內 `GET /api/integrations/status` 回 HTTP 200，三個 health probe 都是 200。2026-11-22 production image `0052fa5430b7…` 的 ChatGPT browser 授權 System／Registry 已另行覆驗，結果見本節最新 production checkpoint。
  - [x] Backstage `/healthcheck` 回 200；以 Agent UI 容器呼叫 Catalog entities API 時回 401，故新 UI 只顯示 Backstage backend health，不讀 Catalog records。Gateway 與 Langfuse health 探測只顯示 HTTP status，不讀探測回應本文。
  - [x] 覆蓋盤點已完成，並將未達的整合結果分開記錄：Backstage Guest Catalog 有 48 entities／366 relations，Catalog Graph 已設定 root 並以 browser 驗到節點／關係；Langfuse project API 有 1 project，2026-11-22 最新 traces 觀察為 14,763，10 筆抽樣未見 AgentOS run/session 關聯，datasets 為 0。本輪沒有啟動模型 run；外部服務斷線時的 UI source isolation 仍未做故障注入。整合限制由 F16／V04b 追蹤，見[驗收證據](agent-ui-verification-evidence.md)。

  3.2.1 live OpenAPI 的標準 tags 已逐項歸入下表；另有 5 個未帶 tag 的 POC Factory extension operations。標成「路由待驗」表示只由 OpenAPI 確認存在，不能視為已配置、授權或有資料。共 94 paths／135 operations；完整 methods、parameters、schema refs 與 OpenAPI security 見 [inventory](agentos-api-openapi-3.2.1.md)。

  | OpenAPI tag | UI／能力家族 | 3.2.1 當前狀態 |
  | --- | --- | --- |
  | Agents | F03／F07／F08 | Agent list/detail 有讀取；Runs 已抽驗。執行、取消、續跑與 checkpoints 尚未驗。 |
  | Approvals | F14 | 無 Authorization 回 401；帶 Authorization 的 GET 回 503 並含 configuration-dependent `detail`。無待審資料證據或管理 UI；disabled/write operation 仍未執行。 |
  | Components | F17 | 無 Authorization 回 401；帶 Authorization 的 GET 回 503 並含 configuration-dependent `detail`。沒有管理 UI；不能將此 503 解讀成成功空集合。 |
  | Core | F01／F06／F16 | `/config`、`/info` 已讀；支援 Overview、目錄與 System 摘要。 |
  | Database | F16／F17 | migration operations 只確認路由；沒有 UI 或 migration 操作驗收。Session DB 選項來自 `/config`。 |
  | Evals | F13 | `GET /eval-runs` 已授權實查 200／0 items，並由新 Evals UI 顯示成功空狀態；create/detail/update/delete 的非空資料與寫入行為未驗。POC runner／公開 fixtures 存在，但沒有 Langfuse dataset run、A/B score 或 trace correlation。 |
| FileSystem | F02／F17 | OpenAPI 為 4 個唯讀 GET：entries／files／search／content，search 的 `query` 與 content 的 `path` 必填，且需 namespace 或 agent_id。未指定 scope 的 `/filesystem/files` 回 200／空陣列；帶 `agent_id=factory-09` 的四個 route 均回 404 `This agent does not have a filesystem`，不代表成功空內容。 |
  | Health | F01／F16 | `/health` 實測 200；Overview 與 System 可讀。 |
  | Knowledge | F09 | `/knowledge/config`、`/knowledge/content` 未帶 `db_id` 回 503；指定已選 DB 後回 404，符合沒有可用 Knowledge instance。沒有內容／搜尋結果；UI 已呈現未配置狀態。 |
  | Learnings | F10 | 選定 DB 的清單回 200／0 items；有紀錄時的欄位、分頁尚未驗。 |
| Media | F02／F07 | `GET /sessions/{session_id}/media/{storage_key}` 的 OpenAPI 宣告 JSON／octet-stream 200。現有 session list 結構未發現 media reference；以既有 session 與不存在 key 唯讀查詢回 503 `Media storage is not configured on AgentOS`，沒有取得或下載 media。 |
  | Memory | F10 | 選定 DB 的清單回 200／0 items；有紀錄時的欄位、分頁尚未驗。 |
  | Metrics | F12 | `/metrics` 已讀到 2 日資料並驗篩選錯誤；`/os/metrics/*` 六個端點中 5 個回資料、users 因未配置 `user_directory` 回 503，六張獨立 read-only 卡已部署。Image `c2f78c7…` 已驗單日 1 run／100% success 對應 0% failure、零 runs 對應 N/A、單日零 tokens 與空日期；2026-11-22 isolated fixture 補驗 2 runs／0% success 與 missing `total_tokens` 欄位。AgentOS 3.2.1 source 確認 date filters inclusive。真實失敗 run、成本仍待驗。 |
  | Queue | F14／F17 | 無 Authorization 回 401；帶 Authorization 的 GET 回 503 並含 configuration-dependent `detail`；無 queue UI 或資料。 |
  | Registry | F17 | 已有唯讀清單、resource type／name 篩選、分頁及白名單 metadata 摘要。production image `0052fa5430b7…` 的授權 browser 已驗 69 筆／7 頁、page 2、type/name 篩選及 Clear；Registry 是全域來源，沒有 `db_id` filter。POC Factory revision 由自有 extension 提供，與 Registry 是不同來源。 |
  | Schedules | F15 | 無 Authorization 回 401；帶 Authorization 的 GET 回 503 並含 configuration-dependent `detail`；無排程 UI 或資料。 |
  | Service Accounts | F17 | 無 Authorization 回 401；帶 Authorization 的 GET 回 503 並含 configuration-dependent `detail`；無帳號管理 UI 或資料。 |
  | Sessions | F07 | Agent／Team／Workflow list、runs 與 run detail 已抽驗；compactions 回 200／0；寫入操作未加入唯讀交付。 |
  | Teams | F04／F07／F08 | Team detail 與 Team Runs 有抽驗；執行及控制操作尚未驗。 |
  | Traces | F11 | Traces／session stats 成功回 0；未知 trace 404 已驗。真實 trace detail 與正向 run 關聯未驗。 |
  | Workflows | F05／F07／F08 | Workflow definition、sessions／runs／detail 已抽驗；送出、續跑與取消未驗。 |
  | POC Factory extension（無 tag） | F01／F03～F06 | `/factory/revision`、`/factory/catalog`、Agent／Team／Workflow definitions 已按現況抽驗；catalog 無 Token 401、已知 definition 200、未知 ID 404。 |

### P3　按實際需求開放操作

- [ ] **P3.1 收斂 F08 的執行範圍。** 後端驗證可選 workflow、工單與情境。一般操作的輸入與 headers 使用白名單，實驗專用 fixture、variant、workspace override 只走實驗路徑。以一筆測試工單驗明確送出、保存、取消與重整。串流中斷只查原 run；若該版本支援事件重連，從已收事件位置 resume。continue 只在 run 確實暫停且要求補資料時使用。送出逾時且查不到 ID 時標「結果未確認」，禁止自動重新提交。
- [x] **P3.2 完成寫入責任評估。** 逐項核對需求／授權狀態、操作目標、影響與重複提交防護，見下表。此計畫目前以 P0～P2 唯讀交付為主；沒有使用者特定的寫入目標／確認，也沒有已配置的使用者角色權限，故本次不加入或呼叫任何寫入操作。

| 操作群組 | 需求／權限現況 | 目標與影響 | 重複提交處理 | 本 POC 決策 |
|---|---|---|---|---|
| Agent／Team／Workflow run 的送出、取消、continue、resume、fork、compact | UI 目前沿用共享本機 Token；沒有每位使用者的角色或 run 操作授權證據。 | 目標須固定 agent／team／workflow、session、run；送出／continue／resume 會啟動模型並可能產生成本及新增 run，cancel／fork／compact 會改變或新增持久狀態。 | OpenAPI inventory 未列 idempotency key；逾時無 run ID 時標示結果未確認，不自動重送。取消／續跑前先讀取精確 run 狀態。 | P3.1 需先取得具體測試工單、情境及明確送出授權；未執行。 |
| Approvals／HITL 決策 | GET `/approvals` 現況為 503；寫入操作是 disabled route stub，無可讀待審記錄或可驗證角色權限。 | 目標須含 approval ID、關聯 run、依據與決策；批准／拒絕可能續跑模型或改變業務流程。 | 每次只作用於明確 approval/run；提交逾時先查目前決策，不盲目重送。 | 不提供寫入按鈕，待 AgentOS 端點啟用並確認審批者授權及審計欄位。 |
| Schedules 異動 | GET `/schedules` 現況為 503；POST／PATCH／DELETE 等均為 disabled route stub。 | 目標須是明確 schedule ID；改動時區、週期、enabled 或 target 會改變未來執行。 | 不假定支援 idempotency；更新後讀回 schedule 狀態再顯示結果。 | 不提供異動；先要有已配置 schedule、owner 授權與變更審核。 |
| Knowledge 匯入／更新／刪除／refresh | Knowledge instance 未配置；既有 UI 只讀。 | 目標需明確 db_id、knowledge_id、content/source；匯入與 refresh 會改變索引／內容，remote URL 可能取回外部資料。 | 不假定 source 去重或重試安全；逾時先查 content/status，不自動重匯；刪除前顯示精確內容 ID。 | 維持只讀；啟用前需確認來源白名單、授權、去重與刪除復原方式。 |
| Memory／Learning 修改／刪除 | 當前資料為成功空集合；共享 Token 不能代表對象本人授權。 | 目標需明確 db_id、record ID、user／agent／team/session scope；修改會影響後續上下文，bulk delete 可能移除多筆持久資料。 | 無公開復原／idempotency 證據；不得用自動重試。刪除前需逐筆預覽並確認範圍。 | 維持只讀；需資料 owner 的明確需求、精確 scope 與可稽核紀錄。 |
| Eval run／Metrics refresh | Evals 目前成功空集合；無已驗的 Langfuse dataset run。Metrics refresh 是 POST 且可 background/rebuild。 | eval 可能啟動模型、寫入結果並產生成本；metrics refresh 會重算／寫入彙總資料。 | 不自動重跑 eval；以 run ID／refresh status 查詢既有工作。重複提交前先確認伺服器狀態。 | 目前只顯示讀取資料或空狀態；新 eval 與 refresh 需各自明確操作授權。 |
| Studio publish、Service Accounts、Components 與 DB migration | 管理路由 disabled／503；尚無管理員角色、遷移目標或變更 runbook。 | 可能公開或擴大系統存取、改變 AgentOS 行為、造成 schema／服務中斷。 | 需變更前備份、版本檢查、維護窗口、回復方案及審計；不能以重試處理。 | 不做 UI 寫入；由管理員依獨立部署／遷移流程處理。 |

## 共通驗收與下次接手

- [x] **V01 資料真實性。** 已於[新版驗收證據](agent-ui-verification-evidence.md#v01-page-to-route-evidence-index)逐頁記錄 UI 區域、唯讀 method/path/status 與可核對欄位／筆數；Docker CLI 確認 Agent UI、AgentOS、Agno DB 同屬 `agno-factory-local` Compose project。Run 記錄可重查 ID `5898977d-3a48-4af6-a0a8-12e618b78724`；Trace／Approval 沒有真實記錄或 ID，分別記為空資料與 disabled 503。Browser 不提供 HAR，因此 route mapping 以 UI source 與同部署的唯讀 API 結果交叉核對，沒有宣稱封包層追蹤。
- [x] **V02 失敗與恢復（目前 UI 路徑已驗）。** 真實部署驗證無 Token 的 401、Approvals／Queue 設定型 503 及彼此獨立 Retry；隔離 mock 驗 loading、成功空、403 no-permission、既有 Factory/runtime 404 局部錯誤、一次 503 Retry、fixture socket drop 經 proxy 呈 502 後 Retry 成功、快速 DB A（慢）→B（快）切換後延遲 A 不覆寫 B。UI 會保留 selector 與 Retry。這不代替真實 AgentOS／模型 stream TCP 中止、request-log 隔離或外部服務 outage，仍由 P0.4／F16 追蹤。
- [ ] **V03 窄版與無障礙。**
  - [x] 2.9.0 已驗 Workflow／Agent／Team 的桌機與 590／470／375px 排版，以及 375px／1280px 的 Runs、Data、Observability。Chat、Workflow 分支、Agent 詳情與側欄抽屜畫面留在[歷史驗收證據](agent-ui-verification-evidence.md#historical-verification-evidence-agno-290-ui-checkpoints)。
  - [x] `sha256:8f1269…` 在 ChatGPT in-app browser 的 375×844 viewport 驗 Overview、Runs、Tools、Skills、Models、Observability、System。document/body 寬 375px；Overview 主內容 client／scroll 寬 334px、Tools／Skills／Models 主內容寬 323px，均無水平溢位。前一 image `sha256:bab1260…` 再於 375×844 和 300×675 CSS viewport 切過九個工作區，document/body 無水平溢位；主內容寬分別為 323–334px、248–259px。300×675 是 375px 螢幕 125% zoom 的尺寸代理，不宣稱為實際 zoom。畫面證據目前只存在 browser tool output。[3.2.1 驗收證據](agent-ui-verification-evidence.md#agno-321-ui-verification)
  - [x] 前一 image `sha256:bab1260…` 的 compact sidebar 已驗 keyboard sequence：聚焦 `Collapse sidebar` 後 Tab 到 Overview、再以 Tab 移至 Tools 並按 Enter，會切到 Tools、收合 overlay 且把焦點返回 `Expand sidebar`；Escape 與抽屜外點擊也可收合並還焦點。
  - [x] UI image `sha256:7809386…` 的 Overview 以 ChatGPT in-app browser 設為 375×844、300×675 CSS viewport；兩種尺寸 document/body scroll width 分別為 375px、300px，畫面無水平溢位。這次仍是未登入的 Overview；不可視作已授權資料畫面的重驗。截圖只顯示在工具輸出。
  - [x] 2026-11-22 ChatGPT in-app browser checkpoint 以 viewport override 375×844 檢查 System 與 Runs；當時未能綁定 UI image digest，之後的 image `0052fa…` 又在 System／Registry 重新設為 375×844 並驗 document/body 寬度無溢位。2026-11-23 browser viewport 為 1280×720，前述 375px override 不再生效；新 image 的窄版覆驗仍待完成。
  - [x] 前一 image `sha256:0052fa…` 的 ChatGPT browser 375×844 System／Registry 實測 `innerWidth`、document `scrollWidth`、body `scrollWidth` 都為 375px，Registry 69 筆與篩選控制可讀，沒有水平溢位。最新 image `sha256:c2f78c7…` 本輪在 ChatGPT browser 以 375px 覆驗 Agents／Teams 搜尋、Metrics（有資料與零資料日期）、Overview Retry 及 System；Metrics 的 `innerWidth`、document/body `scrollWidth` 均為 375px，無水平溢位。畫面只在 browser tool output，未存 repo。
  - [ ] 實際 125% 瀏覽器縮放仍未能驗收：ChatGPT in-app browser 沒有可見縮放控制；2026-11-23 再嘗試 Ctrl+Plus 兩次，viewport／畫面仍沒有可辨識變化，故不把快捷鍵嘗試當成 125% 證據。300×675 CSS viewport 是尺寸代理，不替代瀏覽器縮放。
  - [x] 2026-11-22 current browser 375px 純鍵盤核對：Runs 控制項、session、run、step disclosures 可依序聚焦；Enter 可展開／收合 step 並將焦點留在該按鈕。compact sidebar 可由鍵盤打開，Tab 依序遍歷 9 個工作區，Enter 切至 System 後焦點回 Expand sidebar；Escape 關閉 drawer 並還原焦點。所有頁面內容的完整 Tab 稽核與 image digest 綁定仍未完成。
  - [x] 2026-11-22 isolated Workflow fixture 在 375×844 驗 Tree／Graph inspector：初始焦點、Tab／Shift+Tab 循環、Escape／Close 焦點返回均通過；後續 fixture 增加三個 parallel children，Graph 以單欄直向排列且 document/body 無水平溢位。以純鍵盤聚焦 Graph node 後按 Enter 可開啟 inspector，關閉後焦點返回原節點。完整跨頁 Tab 稽核與實際 125% zoom 仍未驗；詳見[驗收證據](agent-ui-verification-evidence.md#agno-321-ui-verification)。
- [x] **V04 相容性與建置。** 2026-11-23 production Docker build 通過 patch check/apply、Next compile、lint、TypeScript 與 static generation；UI image `sha256:335cab6a78137c56a89a6838968edaf798bd32b35ed98f774065bf3267924bb9` 已部署。Docker CLI 確認 `factory-agent-ui` running／3000、`/` 與 `/api/agentos/health` 為 200、未授權 `/api/agentos/config` 為 401；production container 未注入 proxy Token。UI、AgentOS、Agno DB 同屬 `agno-factory-local`，Agno DB healthy，AgentOS 3.2.1。Dynamic `/api/agentos/[...path]` route 已在 image inventory；本次也於 ChatGPT browser 授權載入 System 和 Runs 頁。重建方式見 [POC 操作方式](../README.md)。
- [ ] **V04b 外部整合另驗。** Langfuse web／worker 與相依服務運行，public health 200／3.227.1，AgentOS 啟動日誌顯示 OTel exporter enabled；Langfuse UI 要求登入，尚無已確認的 AgentOS run／session 對應。Gateway `/health`、`/report` 為 200，既有 PAY-482 報告日期為 2026-11-14。Backstage Guest Catalog 有 48 entities／366 relations；Graph 已設 `system:default/ai-factory` root，ChatGPT browser 顯示 Agents、Teams、Skills、Software Delivery 等 nodes 與 relations。外部 health failure isolation 已以隔離 network 注入；未停止真實服務，也未建立新模型 run 或驗實際 trace 匯出。Langfuse correlation remains open；詳見[驗收證據](agent-ui-verification-evidence.md)。
- [ ] **V05 交接證據。**
  - [x] 實作、Docker build/runtime 與待驗項目已記入[實作紀錄](agent-ui-implementation-log.md)。2.9.0 截圖保存在 `docs/screenshots/`。3.2.1 的 System 桌面與 compactions 空狀態已記入[新版驗收證據](agent-ui-verification-evidence.md#agno-321-ui-verification)。
  - [ ] 將 ChatGPT browser screenshot API 的新版 System／Registry 桌面與 375px 畫面另存至 repo。截圖已在 browser tool output 擷取與目視檢查，最新 image 的 Overview／Metrics／System／搜尋畫面也已擷取；目前工具沒有受支援方式寫入 `docs/screenshots/`。只使用 ChatGPT 內建瀏覽器擷取，沒有擷取整個電腦桌面。
- [x] **V06 目前部署能力交接已完成（不代表所有功能家族都已交付）。** P0～P2 的資料來源與可讀／成功空／未配置／disabled／未驗狀態已列於 [V01 route evidence index](agent-ui-verification-evidence.md#v01-page-to-route-evidence-index) 與 [3.2.1 API crosswalk](agentos-api-contract.md#321-live-tag-family-routeconfigauthdata-crosswalk-2026-11-22)；兩條 P1 瀏覽路徑及一筆真實 session → run 有可重查證據。此交接明列已驗能力、已知不可用項目及資料不足項目；仍開放的 Fxx／P0～P3／V03～V05 依各節追蹤，寫入操作獨立由 P3 管理。

## 歷史規劃 review 紀錄（2.9.0，2026-11-21）

- [x] 依 fork 程式修正 F05、F07 與 P1。移植的驗收反例包括 Factory 端點故障、舊 Chat 書籤、Session 認證失敗、Workflow 重試及版本對不上。
- [x] 依 Agno 2.9.0 與本 POC 修正 F08、F10～F14。區分共享金鑰與使用者授權、每日統計與樣本、實驗 trace 與 session 關聯、中央審批與 run 的續跑及串流重連。
- [x] 補足 P0 的前後端版本基準和 V04b 的服務依賴。此次審查以程式碼、映像內的 2.9.0 契約及既有部署證據為準，尚待實作與線上驗收的項目維持未勾選。

## 3.2.1 接手位置（2026-11-21）

以下兩行是 2026-11-21 的歷史接手摘要，不是目前的完整 checklist；後續狀態以本文件前面的 F01～F17／P0～P3／V01～V06 項目與 2026-11-22 production recheck 為準。

- [x] 升級時確認 Compose 拉取公開 `cletus/agno-agentos:3.2.1`。Agent UI 的 3.2.1 驗收 image 為 `sha256:36cb2655b9c86b34613f865b39d29dda4c190c71a530a67d0225f73c6c26c190`。PostgreSQL 遷移、備份、image digest 及本機重建方式見[升級紀錄](agno-3.2.1-upgrade.md)。
- [x] 3.2.1 已驗桌面 System Explorer，顯示 26 Agents、3 Teams、2 Workflows、1 session DB、1 model 與 Factory revision `bdcc8db58b2161b3`。既有 Workflow run 可讀，session compactions 為成功空狀態。[新版驗收證據](agent-ui-verification-evidence.md#agno-321-ui-verification)
截至該 checkpoint 的待驗範圍（歷史快照）：P0.3 靜態 OpenAPI／tag mapping 已完成，當時仍缺逐 operation runtime sampling；另有 P0.4 真實 stream abort／request-log 隔離、P1.3 斷線與跨 DB 深連結、V03 實際 125% zoom／完整鍵盤、V05 repo 圖檔匯出。資料缺口包括 F01 空 sessions、F07 非空 compaction、P2.1 Knowledge／Memory／Learnings、P2.2 Trace detail／正向 Run→Trace。當前狀態已細分在本文件前方 checklist。

### 2.9.0 歷史窄版驗收補記（2026-11-21）

- [x] 在 375px 確認 Workflow 列表、Software Delivery 22 steps／11 agents／1 team、Parallel Verification 三張 Agent 卡片與 Testing Agent 詳情可讀。Chat 標題可折行，輸入框位於主畫面。
- [x] 展開側欄時，抽屜覆蓋畫面，主欄維持完整寬度。[歷史窄版證據](agent-ui-verification-evidence.md#窄版排版)

### 2026-11-22 checklist audit（較早快照，已由下方覆驗更新）

這個 checklist audit 是本輪 production image 建置前的狀態快照：當時 Registry records panel 尚未在授權頁驗收，Docker CLI 也回報 Docker Engine named pipe permission denied。以下新版覆驗已更新這兩個狀態，不把舊快照當成目前部署結果。

- Langfuse、Gateway、Backstage 的 HTTP 200 仍只證明 health endpoint 可回應；project／trace、Catalog Graph 與資料關聯尚未驗。
- V06 與整體計畫仍未完成；後續以本文件現在未勾選的項目及各 checkpoint 記錄為準。

### 2026-11-22 previous production image checkpoint `0052fa…` (superseded)

- [x] 當時 Docker CLI 確認 `factory-agent-ui` 為 running、port `3000`，image ID 為 `sha256:0052fa5430b7eed45fc2d78eb0e29f04f71c7cb76c57252fb28eb7927ade7967`；AgentOS 3.2.1 未重啟。該 image 先後由 `sha256:337b6ded…` 與 `sha256:c2f78c7…` 取代。
- [x] ChatGPT in-app browser 授權 System 頁顯示 AgentOS 3.2.1、26 Agents／3 Teams／2 Workflows、Registry HTTP 200／69 筆／7 頁；page 2 載入不同清單，`team` 為 3 筆，`Governance` 為 1 筆，Clear 還原 69 筆／7 頁。
- [x] 當時同一 image 於 375×844 browser viewport 實測 document/body width 為 375px；Registry 內容與篩選控制無水平溢位。截圖由 ChatGPT in-app browser screenshot API 擷取並於工具輸出檢視；沒有 repo file export path，未擷取整個電腦桌面。
- [x] F04 Observability Team → `factory-21` Agent → Back to Observability Team 已在 production image 驗證，URL 還原來源 Team 並清除 return query。
- [x] image `sha256:337b6ded…` 的窄版 Overview 以 ChatGPT in-app browser 擷取；畫面看得到 Approvals／Queue 503 與 Retry。最新 image `sha256:c2f78c7…` 又覆驗 Overview、Metrics、System 與搜尋畫面。沒有擷取整個桌面。當前 CUA browser API 未提供 viewport override reset；實際 125% 縮放仍未驗，V03 保持未完成。
- V06、F01 成功空 sessions、真實 Knowledge／Memory／Learning／Trace／eval 資料、F07 非空 compaction、F16 外部關聯、P0.3 runtime operation sampling、P0.4 真實 stream abort、P1.3 斷線／跨 DB、P3 寫入授權、V03 實際 125%／完整鍵盤與 V05 repo 截圖檔仍按各節未勾選項追蹤。

# 在開源 Agent UI 加入 Workflow 檢視頁

在 `pocs/agno-tempo` 的 Agent UI（`http://127.0.0.1:3010`）加入 `Workflows` 入口，讓使用者查看目前部署的 `Software Delivery` 和 `Continuous Improvement`。第一版含唯讀流程圖、節點設定和定義版本。拖拉編輯、發布和執行追蹤留待後續需求確認。

## 第二階段：窄版修正與 Workflow／Agent 詳情

截圖中的 `Software Delivery → Candidate Tests Pass → Parallel Verification` 同時包含巢狀條件與平行群組。`Testing`、`Security`、`Reliability` 的卡片寬度不足，名稱被裁切，Agent ID 被擠成多行。現有版面以整個瀏覽器寬度決定欄數，實際空間還要扣掉側欄、Workflow 清單、詳情面板與各層縮排。現有 Agent 節點詳情主要顯示類型和引用 ID，完整的 Agent 定義目前留在 Factory registry 與 AgentOS。

### 待辦任務

- [x] **重現並量出版面問題。** viewport override 設為 737×1000 px，瀏覽器實際 `innerWidth` 為 738 px；`Software Delivery` 主流程欄寬 470 px。已驗收兩個平行群組、兩層 false 分支和側欄收合；590 px CSS viewport（約 125% 等效寬度）無水平溢出。實際 125% browser zoom 仍未測。
- [x] **依容器實際寬度決定欄數。** 條件分支與平行成員改以各自容器寬度和卡片最小寬度排欄；窄時單欄、減少巢狀縮排，名稱與 ID 可換行。737 px 窄版視窗中未見主內容水平溢出。
- [x] **調整清單、流程圖和詳情的分配。** 寬版並列流程圖與詳情；窄版以流程圖為主，節點詳情使用可切換的固定面板，避免壓縮節點卡片。
- [x] **盤點 API 與定義來源。** 從 Docker 中 Agno `2.9.0` 的 OpenAPI 和回應核對 Workflow、Agent、Team 欄位。原生 API 供應執行模型、工具與 Team 成員，唯讀 Factory 詳情 API 補充 registry 定義、Skills、prompt 和 revision。詳情端點使用 AgentOS 認證及欄位白名單，不回傳金鑰或連線憑證。實測 AgentOS `tools` 是 `{ tools: [...] }` 物件，前端已按實際回應格式解析。
- [x] **增加 Workflow 與節點詳情。** Workflow 概覽顯示名稱、ID、說明、revision、步驟數及使用的 Agents／Teams；節點詳情顯示路徑、類型、引用、條件分支、平行成員和已知用途。已載入的完整 Workflow 定義可展開檢視。
- [x] **讓 Agent 與 Team 引用可以深入查看。** Workflow 節點及新增的 Agents 清單都可開啟元件詳情；介面包含 Factory 摘要、輸入輸出、Skills／instructions、runtime model／tools、Team 成員與 prompt。AgentOS 未提供的知識／記憶設定會明確標示不可用。
- [x] **處理詳情載入與切換。** Factory 定義和 AgentOS runtime 資料分開載入；載入、缺漏、404、權限和連線錯誤各自呈現，單一請求失敗不會隱藏另一來源的資料。

### 完成條件

- [x] 使用 Docker Compose CLI 重建並啟動 AgentOS 與 Agent UI，並在內建瀏覽器開啟 [Agent UI](http://127.0.0.1:3010)。兩個 Workflow、側欄開合及窄版均已實際驗收；590 px CSS viewport 作為 125% 等效寬度通過，實際瀏覽器 125% zoom 尚待驗收。重開機後一般 shell 的 Docker named pipe 曾回 `Access is denied`；使用已核准的唯讀 Compose 檢查確認服務正常運作。
- [x] `Parallel Verification` 的 `Testing`、`Security`、`Reliability` 名稱及引用 ID 都能讀到，三個 Agent 節點均可點開詳情；兩層條件的 true/false 路徑可見。名稱與 ID 留在卡片範圍內，窄版流程只需垂直捲動。
- [x] 以 `Testing`（`factory-09`）核對摘要、Skills、輸入輸出、instructions 與 runtime model/tools。從 `Knowledge Team` 點選 `Research`（`factory-12`）可進入 Agent 詳情；Governance Team 的 `Cost Control`（`factory-27`）也已驗證。`SDLC Ticket & Spec Assistant` 的模型與工具在前一輪瀏覽器驗收可見。不同節點的 ID、Factory revision 對應部署資料。
- [ ] 補驗缺少 Workflow 定義與斷線端點時的錯誤畫面。兩個流程切換、步驟與引用已對照目前 registry；畫面 revision `4de47f618e205ed9` 與 API 回應一致，Factory 詳情 API 採欄位白名單、不回傳金鑰或連線憑證。Agent/Team 聊天送出不屬於本次唯讀 Workflow UI 驗收範圍。

### 第二階段驗收進度（2026-11-18）

- [x] 前端 TypeScript、Prettier、ESLint 檢查通過；Docker production build 成功，patch 已套用並重啟 `agent-ui`。
- [x] Docker 中的 AgentOS 詳情 API 回傳 `factory-02` Agent、`knowledge-team` Team 及 Factory 定義均為 HTTP 200；無認證請求回傳 401。
- [x] 實際點選 Agent 曾重現前端 `tools.flatMap is not a function`。根因是 UI 將 AgentOS `tools: { tools: [...] }` 誤當陣列；型別與解析邏輯已修正，並重新完成 production build。
- [x] 使用者已在本機 Agent UI 更新 AUTH TOKEN；Agents 頁可載入 26 個 Agent、3 個 Team。選取 `Testing`（`factory-09`）後已看到 Factory 摘要、輸入輸出、2 個 Skills、runtime 模型與 3 個工具，並展開確認 Skill instructions 和 Agent instructions。
- [x] Team 清單切換已驗收：新 bundle 明確 reload 後，從 `Testing` 切到 Teams 不再崩潰；自動選取 `Governance Team`，顯示 2 位 members 與 Team instructions。

## 前一輪交接紀錄（2026-11-18）

### 目前狀態

- 上一輪 Docker Compose 曾啟動 `agentos`、`agent-ui`、`agno-db`、`tempo`；重開機後四個容器都已停止（`Exited 255`），需再啟動才能繼續瀏覽器驗收。
- `agent-ui.patch` 是前端唯一的持續修改來源；Docker build 已成功套用，Next.js production build 通過。暫存 clone `.agent-ui-work` 已清除；續作時需從 `Dockerfile.ui` 鎖定的 upstream commit `6dad9593fca6756e1813e4f4b3b2620be6377691` 重新 clone，再套用 patch 編輯與產生新 patch。
- 瀏覽器 token 已由使用者在本機 UI 更新，無需再請使用者提供或在聊天中貼出金鑰。

### 已驗證畫面

- Agents 頁顯示 26 個 Agent、3 個 Team。`Testing` Agent（`factory-09`）的 Factory role、summary、inputs、outputs、revision、2 個 Skills，以及 AgentOS model/provider/integration 和 3 個 runtime tools 都能顯示。
- Skills instructions 與完整 Agent instructions 都可展開；知識與記憶設定明確標示 AgentOS component details API 未提供。
- 當時窄版視窗已設定為 737×1000 CSS px；主區域未見水平溢出。當時尚未捲到 `Parallel Verification`，現已於 2026-11-19 驗收完成，詳見續作紀錄。

### Team 篩選錯誤重現

1. 開啟 Agents 頁，選取 `Testing`（`factory-09`）。
2. 展開任一 Skill 及 Agent instructions（確認詳情頁已正常載入）。
3. 點選清單的 **Teams** 篩選。
4. 頁面崩潰，瀏覽器 console 顯示：`TypeError: Cannot read properties of undefined (reading 'length')`，堆疊位於產生後的 `app/page-*.js` 元件函式 `tS`。

目前還沒有確認是哪個呼叫點；`agent-ui.patch` 中應優先檢查這些直接讀 `.length` 的位置：

- Agent 列表計數：`agents.length`、`teams.length`、`filteredComponents.length`、`components.length`。
- Agent/Team 詳情：`agentDefinition.skills.length`、`teamDefinition.members.length`。
- Workflow 分支中的 `steps.length` 和選取 Workflow 的 `definition.steps.length`（此錯誤發生於 Agents 頁，因此優先度較低）。

已向使用者列出待驗證假設：Teams 篩選改變選取狀態後，詳情頁讀到缺漏欄位；清單切換期間陣列尚未載入；或 Team runtime 的 `members`／`tools` 回傳形狀不符。Docker API 曾直接驗證 `knowledge-team` runtime 有 4 個 members，Factory definition 也有 4 個 members；下一步應先檢查 AgentExplorer 的篩選／選取狀態轉換，再核對 Team 專屬詳情的可選欄位是否都加上防護。

### 當時交接步驟（部分已完成）

1. 重新 clone 固定版本 Agent UI，套用 `pocs/agno-tempo/agent-ui.patch`；檢查 AgentExplorer 篩選、選取狀態和 ComponentDetails 的 Team 分支，找出會對 `undefined` 讀 `.length` 的實際位置。
2. 以「Agents → 選 Testing → Teams 篩選」重現；修正後確認切換不再崩潰，再開啟 `Knowledge Team`，驗收成員清單及點選成員進入 Agent 詳情。
3. 跑 TypeScript、ESLint、Prettier；重新產生 LF patch，確認乾淨 upstream clone 可套用，再用 Docker Compose 重建並啟動 `agentos` 與 `agent-ui`。
4. 在內建瀏覽器完成 Team 頁驗收，接著到 Workflows 的窄版 `Software Delivery` 捲至 `Parallel Verification`，確認 `Testing`、`Security`、`Reliability` 卡片寬度、換行、可點選性、條件 true／false 與 Agent 詳情抽屜；再驗收 `Continuous Improvement` 和 Agents 清單。
5. 完成瀏覽器驗收後，更新本文件的未完成條件，並依 CUA 使用規則結束瀏覽器操作。

## 續作紀錄（2026-11-19）

- 使用者要求把 Agent UI 原始碼修正、畫面截圖與變更說明 commit 並 push 到 `CletusLee/agent-ui`。目前 workspace 是另一個 repository（`AI-Software-Factory-Lab`），UI 原始碼保存在 patch；將在獨立工作目錄還原 pinned upstream 及 patch，確認目標分支後提交。一般沙箱中的 `gh` 連線失敗且顯示 token 無效，正進一步確認網路與驗證狀態。
- 已透過核准的網路存取確認 GitHub 登入正常、目標 fork 的 `main` 位於 `6dad9593fca6756e1813e4f4b3b2620be6377691` 且具管理權限；已 clone 至 `agent-ui-delivery` 並成功套用 patch。接著整理截圖與依賴說明後提交。
- 已新增兩張 Docker UI 截圖、英文變更與使用說明，並附上 `AI-Software-Factory-Lab` 後端詳情 API patch；文件註明 `/factory` 非 Agno 標準 API、套用基準及尚未驗收項目。截圖已收合側欄，沒有顯示認證欄位。正在檢查並準備 commit。
- 已建立目標 repo commit `817a009`（`Add workflow and agent explorers`），包含前端、後端 integration patch、說明及兩張截圖；staged `git diff --check` 通過，正準備 push。
- 已 push 至 `CletusLee/agent-ui` 的 `main`；以 `git ls-remote` 確認遠端指向 `817a009b3d7e407b17b48872f5bbf1c5055b5955`。交付 clone 位於 `agent-ui-delivery`，工作樹乾淨。原本專案的 Dockerfile、README、app.py、patch 和本交接文件仍是原專案未提交的工作；Agent UI repo 內提供後端 patch，不會自動更新該原專案。
- 使用者重新開機後恢復工作；本機 Agent UI 瀏覽器分頁仍開啟。重啟後瀏覽器保存的 AUTH TOKEN 曾遭 AgentOS 拒絕；使用者重新貼入當前 `.env` 值後，AgentOS 清單與詳情恢復正常。
- 已重新確認上一輪的 Team 篩選錯誤：在 Agents 頁選取 `Testing` 後點 **Teams**，頁面崩潰並顯示 `Cannot read properties of undefined (reading 'length')`。
- 目前診斷方向依序為：AgentExplorer 的篩選／選取切換使詳情讀到未載入欄位；清單切換時陣列暫時為 undefined；Team 詳情對可選欄位未做防護。`agent-ui.patch` 中的直接存取點包含 `agentDefinition.skills.length` 與 `teamDefinition.members.length`，以及 Agent/Team list count；尚未證實實際 throw 點。
- **根因已由重現路徑和 patch 控制流程確認：** AgentExplorer 切換 `kind` 時沒有同步清掉舊的 `selectedId`；ComponentDetails 也沒有依 `kind`／`id` 隔離 instance state。第一次 Team render 會暫時拿舊的 Agent definition 作為 Team definition；effect 清除舊 definition 之前，`teamDefinition.members.length` 讀到 undefined 並造成例外。AgentOS Team 與 Factory API 本身都有回傳 members，這是前端切換時的舊資料競態。
- **修正方向：** 切換 Agent／Team filter 時同步清空 selection；讓 ComponentDetails 在 `kind`／`id` 改變時使用新 instance，並將可缺漏的 `skills`／`members` 正規化為空陣列，避免同類資料轉換再崩潰。
- 重開機後以 `docker compose up -d agentos agent-ui` 成功重新啟動 `agentos`、`agent-ui`、健康的 `agno-db` 與 Tempo。從執行中的 UI container 確認 `/ui/.git` 位於固定 commit `6dad9593fca6756e1813e4f4b3b2620be6377691`，且工作樹已套用目前 patch。
- 已從 UI container 取回 pinned source、`.git` 與必要設定至 workspace 暫存目錄 `.agent-ui-work`；排除 `node_modules` 和 `.next`（避免複製約 842 MB build/dependency 資料）。
- Serena instructions 工具未出現在本次可用工具清單；repo 內也沒有 `AGENTS.md`、`GLOSSARY.md` 或 ADR 命中。沿用既有固定 upstream commit 與 patch 工作方式。
- 已在 `.agent-ui-work/src/components/factory/AgentExplorer.tsx` 實作：切換 Agent／Team 類別時清空舊 selection，且將同類別點選設為 no-op；`ComponentDetails` 使用 `${kind}:${selectedId}` 作為 React key，讓新元件不會短暫沿用另一筆詳情 state。
- 已在 `ComponentDetails.tsx` 將 skills／members 缺漏正規化為空陣列。Prettier、TypeScript `tsc --noEmit`、ESLint 均通過；patch 已重新產生（LF、0 CRLF），`git diff --check` 通過。
- Docker production build 成功：固定 upstream commit 可套用更新後的 patch，Next.js production build、lint 與型別檢查通過。
- 新 Agent UI image 已以 Compose 重建並啟動。AgentOS log 曾記錄瀏覽器 `GET /agents` 為 401，而容器內當前 `OS_SECURITY_KEY` 呼叫同一路徑回 200；使用者重新同步 AUTH TOKEN 後，Agents 清單恢復為 26 個 Agent、3 個 Team。
- 第一次點 Team filter 時頁籤仍使用舊的 client bundle；明確 reload 新 production bundle 後，從 `Testing` 切到 Teams 成功，顯示 `Governance Team`、2 位 members 及 Team instructions，無前端例外。
- 已從 `Governance Team` 點選 `Cost Control`，成功切至 Agents 清單並開啟 `Cost Control`（`factory-27`）Agent 詳情。
- `Continuous Improvement` 在窄版顯示 6 個 steps、2 個 Agents、2 個 Teams 與 revision；點選其中 `Observability Team` 可看到 Team instructions、4 位 members 和 runtime 詳情。
- 在 viewport override 737×1000 px（實際 `innerWidth` 738 px、主流程欄寬 470 px）的窄版 `Software Delivery` 中，`Parallel Verification` 的 `Testing`／`factory-09`、`Security`／`factory-11`、`Reliability`／`factory-20` 以單欄顯示，名稱與 ID 可讀，流程只需垂直捲動；DOM 實測 document/body 寬度同為 738 px，無水平溢出。
- 點選 `Testing` 能開啟 Agent 詳情抽屜；關閉後回到原流程位置。往下可見 `Needs Rework` 與 `Needs Evidence or Rework` 兩個 false 分支。
- 窄版 `Continuous Improvement` 顯示 6 steps、2 Agents、2 Teams；點選 `Observability Team` 顯示 4 位 members、Team instructions 和 runtime 資訊。
- 窄版收合側欄後，流程主區增加至 686 px；document/body 仍是 738 px，主區沒有水平溢出。
- 125% 等效寬度測試：將 CSS viewport 設為 590×1000 px（約 737/1.25），`Software Delivery` 的 `Parallel Verification` 與 `Parallel Proposals` 都維持單欄；`Testing`、`Security`、`Reliability`、`Code Proposal`、`Infrastructure Proposal`、`Integration Proposal` 的名稱和 IDs 可讀。兩層 false branch `Needs Rework`／`Needs Evidence or Rework` 也完整顯示。document/body 為 590 px、收合側欄後主區 538 px，無水平溢出。此為等效 viewport 測試；Ctrl+Plus 未改變實際 `devicePixelRatio`，所以實際 125% browser zoom 尚未測。
- 125% 等效寬度測試：將 CSS viewport 設為 590×1000 px（約 737/1.25），`Software Delivery` 的 `Parallel Verification` 與 `Parallel Proposals` 都維持單欄；`Testing`、`Security`、`Reliability`、`Code Proposal`、`Infrastructure Proposal`、`Integration Proposal` 的名稱和 IDs 可讀。兩層 false branch `Needs Rework`／`Needs Evidence or Rework` 也完整顯示。document/body 為 590 px、收合側欄後主區 538 px，無水平溢出。此為等效 viewport 測試；Ctrl+Plus 未改變實際 `devicePixelRatio`，所以實際 125% browser zoom 尚未測。
- 從 `Knowledge Team` 點選 `Research`（`factory-12`）後，Agent 詳情可顯示 Factory role、summary、輸入輸出、revision、Skill、instructions、runtime model、integration、3 個 tools，並清楚標示 API 未提供的 knowledge/memory 設定。
- 本次重開機續作：內建瀏覽器仍可讀取 Agents/Teams 與 Research 詳情（26 agents、3 teams，revision `4de47f618e205ed9`）。PowerShell 的 Docker Compose/CLI 呼叫 `dockerDesktopLinuxEngine` named pipe 得到 `Access is denied`；`Get-Service` 讀取 Service Control Manager 也被拒，因此這是本次 shell 權限/daemon 通道限制，不代表 UI 或 AgentOS 已停機。
- 本次以唯讀 Docker Compose 檢查確認：`agent-ui`、`agentos`、`tempo` 為 `Up`，`agno-db` 為 `Up (healthy)`；UI 對宿主機綁定 `127.0.0.1:3010`，AgentOS 綁定 `127.0.0.1:7877`。
- 已還原臨時 viewport override，內建瀏覽器切回 `Workflows → Software Delivery`；頁面可見 22 steps、1 agent、1 team、definition revision `4de47f618e205ed9`，節點引用與兩層 true/false 分支均已載入。
- 已清理由容器取出的暫存 clone `.agent-ui-work`；後續持續修改以 `pocs/agno-tempo/agent-ui.patch` 為準，不需依賴暫存資料夾。
- **尚待補驗：** 實際瀏覽器 125% zoom（目前只通過 590 px CSS viewport 等效驗收）、缺少 Workflow／斷線端點的錯誤畫面。後續可從本段繼續。
- 本次 `docker compose exec agent-ui` 起初因容器已停止而失敗；`docker compose ps -a` 確認四個容器均於重開機後退出。之後 Compose 已成功啟動，且容器內來源 commit 已確認。

## 實作任務

- [x] **確認前端基準。** Clone `agno-agi/agent-ui` 並切到 `Dockerfile.ui` 鎖定的 `6dad9593fca6756e1813e4f4b3b2620be6377691`，並以實際 AgentOS API 回應確認 Workflow 資料形狀。
- [x] **提供正在使用的 Workflow 定義。** 在 AgentOS 加入唯讀 `GET /factory/workflows/{workflow_id}`，回傳流程名稱、說明、步驟樹與載入版本的 `revision`。未知 ID 回傳 `404`。
- [x] **加入 Workflows 頁面。** 加入入口，沿用目前選取的 AgentOS endpoint 與認證設定。用 `GET /workflows` 顯示列表，載入定義並處理載入中、空列表、連線失敗和定義找不到的狀態。
- [x] **顯示流程圖與節點設定。** 依步驟順序顯示流程、條件分支和平行群組。節點詳情顯示類型、引用和內建 Python gate 說明，頁面顯示定義版本。
- [x] **納入目前的 Docker build。** 將前端改動存成 `agent-ui.patch`，更新 `Dockerfile.ui` 於固定 commit 上套用 patch，並更新 README 使用說明。

## 驗收結果（2026-11-18）

- [x] TypeScript 型別檢查與 Prettier 格式檢查通過。
- [x] Next.js production build 成功。
- [x] `agent-ui.patch` 可套用到乾淨的上游 commit，且套用後 `git diff --check` 通過。
- [x] AgentOS app 與 registry 模組的 Python 語法檢查通過。
- [x] Docker Compose 成功建置 `agentos` 與 `agent-ui`，並啟動 `agentos`、`agent-ui`、健康的 PostgreSQL 與 Tempo 依賴。
- [x] 宿主機呼叫 `GET /workflows`、`GET /factory/revision`、兩個 `GET /factory/workflows/{id}` 均回傳 `200`。Revision 為 `4de47f618e205ed9`，workflow 數量為 2。
- [x] 在 ChatGPT 內建瀏覽器實際開啟 `http://127.0.0.1:3010`，可切換兩個 workflow；`Software Delivery` 顯示條件分支、平行群組與後續人工審查，點選 `Readiness` 和 `Parallel Proposals` 時右側資訊正確更新。
- [x] 於當時的桌面視窗驗收分支堆疊及流程區捲動。後續截圖發現部分寬度仍有巢狀卡片擠壓，已列入第二階段待辦。

## 驗收條件

- [x] 使用 `agno-factory-tempo` Compose build 並啟動服務後，可從 `http://127.0.0.1:3010` 的側欄開啟 Workflows 頁面，並選取 `Software Delivery` 和 `Continuous Improvement`。
- [x] `Software Delivery` 的圖呈現 `is_ready`、`candidate_passed` 的 true/false 分支與兩個平行群組。`Continuous Improvement` 依部署定義呈現 6 個順序步驟。選取條件節點與平行群組時，右側設定會顯示正確類型、引用與說明。
- [x] 畫面的定義版本 `4de47f618e205ed9` 與 `GET /factory/revision` 回傳值一致。
- [ ] 尚未在瀏覽器刻意切換到斷線端點或不存在的 workflow 來驗收錯誤狀態；也未送出 Agent/Team 聊天訊息做端到端驗收。Agent 與 Team 清單、既有 session 載入成功。

## 參考

- [開源 Agent UI](https://github.com/agno-agi/agent-ui)
- [AgentOS Workflow 列表](https://docs.agno.com/reference-api/schema/workflows/list-all-workflows)與[詳情 API](https://docs.agno.com/reference-api/schema/workflows/get-workflow-details)
- [Agent UI 建置](../Dockerfile.ui)、[AgentOS 設定](../app.py)與[定義載入器](../integration/registry.py)
- [Software Delivery 定義](../../../definitions/workflows/software-delivery/workflow.json)與[Continuous Improvement 定義](../../../definitions/workflows/continuous-improvement/workflow.json)

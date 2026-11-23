# Agno 3.2.1 升級與 Agent UI 相容性 Checklist

建立日期：2026-11-21（台灣時間）  
目標：將 `pocs/agno` 從 Agno 2.9.0 升到官方最新穩定版 3.2.1，確認 AgentOS、PostgreSQL schema、Factory workflows、Agent UI 與 Docker 執行環境一致。升級過程每完成一段就更新本文件及 [實作紀錄](agent-ui-implementation-log.md)。

## 版本核對

- [x] 官方 Agno GitHub Releases 將 v3.2.1 標為 Latest，發布日期 2026-11-17；release commit 為 `2e9a452`。來源：[Agno Releases](https://github.com/agno-agi/agno/releases)。
- [x] PyPI 已發布 `agno==3.2.1`，具 provenance。來源：[agno 3.2.1 on PyPI](https://pypi.org/project/agno/3.2.1/)。
- [x] 升級前基線為 `agno[os]==2.9.0`，lock 固定 `agno==2.9.0`；升級前 Docker AgentOS `/info` 顯示 2.9.0。這是歷史基線，不是目前版本。

## 升級工作

### 1. 相容性盤點及恢復準備

- [x] 確認本 POC workflow 建構呼叫 `Workflow(id=...)`，符合 v3 keyword-only constructor。
- [x] 搜尋目前 AgentOS／workflow source，沒有發現 v2 flat HITL kwargs、已移除 Agent／Team memory/history kwargs、`continue_run(updated_tools=...)`、`reasoning=True`、移除的 JWT/MCPToolbox 參數。
- [x] 檢查 v2 與 v3 API/OpenAPI 路徑、response schema、run pagination、metrics、tracing、Factory 自訂 endpoints 差異；已保留 2.9.0 歷史 inventory、產生 3.2.1 live 94 paths／135 operations inventory，並更新 [API contract](agentos-api-contract.md) 與 UI model／session-compaction API 型別及 adapter。未抽樣的 runtime operation coverage 另由 P0.3 追蹤。
- [x] 升級前已記錄 PostgreSQL Agno schema 為 `ai`（不是 `public`）；13 張 `agno_*` schema-version table 目前全標記 `2.5.6`。資料量：47 sessions，舊 `runs` JSON 共 59 runs，3 metrics rows，learnings／memories／knowledge／approvals／evals／components／schedules／service accounts 皆為 0。`agno_runs` 尚不存在。
- [x] `pg_dump -Fc` 已建立可讀備份並以 `pg_restore --list` 驗證，host 副本 SHA-256 與容器來源一致；大小 1,903,799 bytes，SHA-256 `dba58add7cebf8f86e90d7e201486ccae0b57d651d6df202c14092ba8d27a4ea`。備份檔 `backups/agno-db-v2-before-3.2.1.dump` 由根目錄 `.gitignore` 排除，只留在本機、不提交 Git、不輸出 secrets。
- [x] 保留升級前可回復的 Agno 2.9.0 image 與原 lock checkpoint，直到 v3 版及 schema 驗收完成；Docker image 清理仍暫緩，後續只能清除本任務產生且已確認沒有容器使用的舊 image。

### 2. 更新 Python／Docker AgentOS

- [x] 將 `pocs/agno/requirements.txt` 固定至 `agno[os]==3.2.1`，以 Python 3.12 重新解析完整 `requirements.lock`；目前 lock 為 `agno==3.2.1`、`agnoctl==0.2.1`、`fastapi==0.165.0`、`pydantic==2.14.4`。第一次解析受執行環境 cache 權限與 PyPI DNS 限制，改用 POC 內 cache 並允許 PyPI 連線後成功。
- [x] 依 v3 migration guide 檢查 Factory Python code；Docker runtime import 首次發現 `Step(on_error=...)` breaking change。3.2.1 的 `Step` 使用 `skip_on_failure`；將 Agent/Team step 改成 `skip_on_failure=False, max_retries=0`，保持原先失敗時不跳過的流程語義。`pending_approval` 仍 fail-closed 檢查必要 step output。
- [x] Docker production build `agno-factory-local-agentos:latest` 成功，image ID `sha256:833882bc1e024e1acbc6ad9ce953c5b4b1bb0239451ea85f28a1ab17f8b013f2`；Compose one-shot runtime import 載入全部 Factory module/workflows 成功，Agno `3.2.1`、app title `Agno AgentOS`、32 registered routes。
- [x] 運行中的 AgentOS `/info` 回報 `agno_version=3.2.1`；`/config` 200、`/openapi.json` 200，OpenAPI 3.1.0／93 paths／134 operations。已從 live schema 產生完整 [3.2.1 operation inventory](agentos-api-openapi-3.2.1.md)。v3 沒有 `/models`（404），可用模型由 `/config.available_models` 提供；摘要契約見 [API contract](agentos-api-contract.md)。

### 3. PostgreSQL v2 → v3 schema migration

- [x] migration 前唯讀保存 DB 基線：schema `ai`，13 schema-version records 均為 2.5.6；47 sessions／59 舊 JSON runs／3 metrics。learnings、memories、knowledge、approvals、evals、components、schedules、service accounts 均為 0。
- [x] 停止 `factory-agentos`（唯一運作中的 Agno DB writer）；gateway 與 catalog exporter 先前已停止。migration 期間保留 PostgreSQL 與 UI，沒有對 Agno DB 的並行 writes。
- [x] 以 v3.2.1 `MigrationManager(PostgresDb(...)).up()` 遷移同一 PostgreSQL DB，Agno 最新 storage schema 為 `3.0.0`。所有可遷移 table migration 成功完成，session migration 複製 59 runs；learning re-key `scanned=0, keyed=0, rekeyed=0, merged=0, quarantined=0, contaminated=0, contaminated_keyed=0, unowned=0, malformed=0, conflicts=0, failed=0, purged=0`。
- [x] v3 建立 `agno_runs` 並保留 `agno_sessions.runs` 備份欄。本次未呼叫 `cleanup_legacy_runs_column(force=True)`，也未刪除 legacy 欄。
- [x] migration 後仍為 47 sessions、59 `agno_runs`，legacy JSON backup 仍有 59 runs、3 metrics、0 learnings；12 個已遷移主要 storage tables 都有 `user_id` 欄。`agno_schema_versions` 有 15 個 3.0.0 records；空的 `agno_component_configs`、`agno_component_links`、`agno_service_accounts` 仍記錄 2.5.6（v3 manager 沒有為其登錄 migration）；另有未實體建立的 Company table version entries。保留這些 legacy/empty tables，不手動改 schema。
- [x] 驗證升級後 AgentOS 可啟動並通過 `/health`、`/info`、`/config`、`/openapi.json`、Factory revision、Workflow Runs UI；`/sessions/{session_id}/compactions` 回 200 空 array。既有 UI Runs／Metrics／Trace 頁的資料與成功空狀態亦已經部署版本驗收；compactions 元件列在 Runs session detail。
- [x] migration 後數量抽查：47 sessions、59 normalized `agno_runs`、59 legacy JSON backup runs、3 metrics；本次資料庫沒有 compaction rows。UI 成功呈現 compactions 的 empty state，沒有虛構摘要或封存訊息。
- [x] 本次 migration 未發生不完整狀態；已保留可讀備份，未刪除 legacy runs 欄。回復／診斷條件未觸發，因此未執行 rollback 或重跑 migration。

### 4. Agent UI 調整與驗收

- [x] System Explorer 由 `/info` 顯示實際 Agno 3.2.1；畫面顯示 health、runtime version、Factory revision、Agents／Teams／Workflows counts、DB、models、interfaces；外部 integration 未查證時維持 `Not checked`。
- [x] 對照 v3.2.1 OpenAPI；UI 新增 `/config.available_models` projection 及 `/sessions/{session_id}/compactions` 型別、載入、空狀態、錯誤／Retry，不把 v2 `/models` 當成 v3 endpoint。
- [x] v3.2.1 session compactions API (`GET /sessions/{session_id}/compactions`) 唯讀呈現；當前真實 Workflow session 成功回傳空集合，UI 顯示成功空狀態。
- [x] 部署版 Sessions/Runs、Workflow config/run detail、Data、Metrics、Trace 與 System Explorer 都能載入或顯示正確的空／未檢查狀態；本輪實際重驗 Workflow Run 與 System。
- [x] Agent UI Docker production image 建置、部署、browser reload；有效 Token 由使用者先輸入在 UI。畫面顯示 AgentOS 3.2.1、26 Agents、3 Teams、2 Workflows；Runs compaction empty state 已於前一驗收流程確認。
- [x] 桌面版 System Explorer 目視確認，Token 遮罩。當前 in-app browser 截圖已在工作階段輸出；本次工具未能將這張新圖寫成 repo 中的 JPEG/PNG，故永久檔案證據待補。375px viewport override 沒生效，不宣稱本輪 3.2.1 窄版驗收通過。

## 官方升級依據與已知 breaking changes

- [Agno 3.2.1 release notes](https://github.com/agno-agi/agno/releases)：3.2.1 新增 session compactions 與 Company files API；其他修正包含 MCPTools connect outcome、工具 timeout 等。
- [Migrating to Agno v3.0](https://docs.agno.com/other/v3-migration)：session runs 正規化到 `agno_runs`；SQL tables 增加 user isolation 欄位；workflow HITL 改用 `HumanReview`；Workflow constructor 改為 keyword-only；部分 Agent/Team kwargs、`continue_run(updated_tools=...)` 及 `reasoning=True` 移除；v3 learning entity re-key 在寫入期間需停機且不可逆。
- [Database migration endpoints](https://docs.agno.com/agent-os/usage/database-migrations)：支援 `POST /databases/all/migrate` 或 per-DB migration；執行前備份，並檢查 response body；多 DB endpoint 可在部分失敗時回 207。
- [MigrationManager reference](https://docs.agno.com/reference/storage/migrations)：支援版本、table types、資料庫 adapters 與 migration 結果限制。
- [Agno v3.0 changelog](https://docs.agno.com/other/v3-changelog)：v3 storage/schema 行為與 legacy runs 欄位保留策略。

## 目前 checkpoint（2026-11-21）

- [x] 升級前 Docker AgentOS 為 2.9.0；DB 備份仍保留於 `backups/agno-db-v2-before-3.2.1.dump`。舊 AgentOS 2.9.0 image 與已知舊 Agent UI build images 在新版驗收後檢查無 container 引用並清理；此時若回退，需從備份還原 DB 並依舊版 lock 重建 image。
- [x] 已新增本檔作為版本升級 checklist；原本 [Agent UI capability plan](agent-ui-capability-plan.md)、[實作紀錄](agent-ui-implementation-log.md)、[驗收證據](agent-ui-verification-evidence.md) 保留既有工作，不把舊版 UI 驗收冒充新版驗收。
- [x] `requirements.txt` 與 `requirements.lock` 已更新到 Agno 3.2.1；驗收後已移除本次解析產生的 `pocs/agno/.uv-cache`。
- [x] Docker AgentOS 3.2.1 image build、Factory app/workflow import 與 DB migration 全部完成。資料基線與 migration 結果見上方 checklist。
- [x] Agno 3.2.1 `MigrationManager` migration 完成並通過基本資料量核對：47 sessions、59 normalized runs、59 legacy backup runs、3 metrics、0 learnings；v3.0.0 schema records 15，3 個空的 component config/link/service-account tables 保持 2.5.6。legacy runs 欄未清理。
- [x] 新版 AgentOS 已在 Docker 啟動並驗證；瀏覽器 System Explorer 顯示 Agno 3.2.1、health OK、26 Agents、3 Teams、2 Workflows、1 session DB、1 model，Factory revision counts 一致。image ID 為 `sha256:833882bc1e024e1acbc6ad9ce953c5b4b1bb0239451ea85f28a1ab17f8b013f2`；2026-11-23 final Agent UI image `sha256:1d2e02ed08ceab93e13c05066c3021e6e0c0ab897385a2b8df07e93400e7258c` 見下方新截圖待辦。
- [x] 使用者建立正確 namespace 後，已推送 `cletus/agno-agentos:3.2.1`。Docker Hub manifest digest：`sha256:6a13d301661dcef023c1d7d0d5264cd369a68c1cca4cb362698ba6749e77df70`。未登入 Docker Hub API 確認 `is_private=false`，tag `3.2.1` 存在、平台 `linux/amd64`；`docker manifest inspect` 可讀到相同 image config ID。
- [x] POC 預設 Compose 已改用公開 `cletus/agno-agentos:3.2.1`，不會建置 AgentOS；`docker compose pull agentos` 後重新建立 `factory-agentos` 並確認其 image 設定為該公開 tag、容器內 `agno.__version__=3.2.1`。本機重建由 `docker-compose.build.yml` overlay 明確啟用。
- [ ] 將 2026-11-23 final production image `sha256:1d2e02ed08ceab93e13c05066c3021e6e0c0ab897385a2b8df07e93400e7258c` 的 System／Runs 新版 screenshot 存到 `docs/screenshots/`。System／Runs 授權畫面在前一 `335cab6…` image 已於 ChatGPT in-app browser 驗證；final `1d2e02e…` image 僅以 no-token reload／401 覆驗，本次未能設定 375×844 viewport，也未將實際 125% zoom 當成已驗。browser screenshot API 沒有受支援的 repo file export path，因此 repo 圖檔仍未完成。舊 image `0052fa…` 的 375px 結果僅保留為歷史檢查。
- [x] 依使用者要求只清理可歸屬本任務且無 container 引用的 images：舊 AgentOS 2.9.0 image `sha256:05ab1a37ffe66455078e7bba1b16112a7e8bd4dc44874550c267fff828308f44`、11 個舊 Agent UI build images，以及失敗 namespace 的本機 alias `cletuslee/agno-agentos:3.2.1`。目前使用中的 AgentOS `cletus/agno-agentos:3.2.1` 與 UI image 均保留；未清理其他專案 images／containers／volumes。

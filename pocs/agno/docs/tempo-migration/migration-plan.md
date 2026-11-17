# Agno + Grafana Tempo 獨立 POC 實作 Checklist

**狀態**　新 POC、映像與服務已啟動；Agent、Delivery 與含 Continuous Improvement 的完整 Workflow demo、Tempo trace、Agent UI、報告、部署、故障恢復、並行隔離、重啟持久性及回歸驗收均已完成並逐項勾選。僅剩登入後手動檢視 Grafana Explore 與 LibreChat 對話畫面。以現有 [Agno POC](../../README.md) 為基底，在同層建立 `pocs/agno-tempo/`。原本的 `pocs/agno/` 繼續用 Langfuse。新 POC 由 AgentOS 透過 OTLP/HTTP 將 trace 送到 Tempo，操作入口為 Grafana Explore。

## 1. 建立新 POC

- [x] 建立 `pocs/agno-tempo/`，複製原 POC 的已追蹤原始檔、Compose、Dockerfiles、Python 程式與測試、`.env.example`、Agent UI 建置設定，以及 `integration/` 和 `backstage/` 原始檔。來源 commit 為 `e519a423ba3c7ac5ac7ae367da4ff67dfccc99c4`。
- [x] 讓新 POC 沿用 repository 根目錄的 `definitions/`、`scenarios/` 和 `benchmark/`。確認容器掛載與 Python 路徑解析都讀到同一組共用資料。
- [x] 從新 POC 的 `.env.example` 和 `integration/setup_env.py` 建立獨立 `.env` 與隨機服務密鑰。只沿用原 POC 的模型 API key、endpoint 和 model ID。檢查新 `.env` 僅含模型設定、新 POC 密鑰與 Tempo 參數，無 Langfuse 變數。
- [x] 從複製清單排除原 POC 的 `.env`、本機快取、容器資料、執行產物與 Langfuse 截圖。只複製已追蹤的原始檔，排除四張 Langfuse 截圖及本機 `.env`。
- [x] 明確納入 `native_report_template.html`、`deployment/releases/.gitkeep` 與 `swarm-output/.gitkeep`。原 `pocs/agno/` 程式維持未修改；新 POC 與本 checklist 為本次新增檔案。
- [x] Docker Engine 啟動新 POC 後，Compose 成功建立 `integration/catalog/`，`catalog-export` exit 0 並生成 `entities.yaml`。
- [x] 從成功建置的 AgentOS image 擷取 74 個已解析套件版本，產生 `requirements.lock`。實際核心版本為 Agno `2.9.0`、OpenInference Agno `1.2.1`、OTel SDK／OTLP `1.45.2`。
- [x] 將 `requirements.lock` 接入 `Dockerfile.agentos`，以 constraints 固定所有直接與遞移套件。
- [x] 以 lock 重新建置 AgentOS 成功；主要映像版本固定為 Agent UI commit `6dad9593fca6756e1813e4f4b3b2620be6377691`、LibreChat `v0.8.7`、Tempo `3.0.0`、Grafana `12.3.0`。
- [x] 比較重建 image 的 `pip freeze` 與 `requirements.lock` 完全一致，74 個套件版本相符。
- [x] 靜態確認新 POC `.env`、執行報告、catalog 與 deployment 快照符合 Git 忽略規則；`.env.example` 可納入版控，`swarm-output/.gitkeep` 與 `deployment/releases/.gitkeep` 存在。
- [x] Compose 首次啟動建立 `integration/catalog/entities.yaml`，且檔案符合 Git 忽略規則。

## 2. 隔離 Compose、資料與本機入口

- [x] 新 `docker-compose.yml` 使用 `name: agno-factory-tempo`。移除固定 `container_name`，確認 PostgreSQL、MongoDB、uploads、Grafana、Tempo 使用獨立 volumes。`docker compose config` 顯示專案名稱 `agno-factory-tempo`，並成功解析服務設定。 [Docker Compose 專案名稱](https://docs.docker.com/compose/how-tos/project-name/)
- [x] 替換新 POC 自建映像的標籤。`agentos`、`agno-gateway`、`catalog-export` 使用 `agno-factory-tempo-agentos:local`，Backstage 使用 `agno-factory-tempo-backstage:local`。Agent UI build 使用新 POC 的 `OS_SECURITY_KEY`。
- [x] 新 POC 的主機埠已依下表綁定 `127.0.0.1`，Compose 設定驗證通過。原 POC 使用的埠號維持原設定。 [Docker Compose 網路](https://docs.docker.com/compose/how-tos/networking/)

  | 服務 | 原 Agno POC 主機埠 | 新 Tempo POC 主機埠 | 容器埠 |
  | --- | ---: | ---: | ---: |
  | Agent UI | 3000 | 3010 | 3000 |
  | Agno AgentOS API | 7777 | 7877 | 7777 |
  | Agno Gateway（含 `/report`） | 7778 | 7878 | 8080 |
  | LibreChat | 3080 | 3090 | 3080 |
  | Backstage | 7007 | 7107 | 7007 |
  | Agno PostgreSQL | 5532 | 5632 | 5432 |
  | 追蹤介面（原 Langfuse／新 Grafana） | 3001 | 3002 | 3000 |
  | Tempo 查詢 API | — | 3200 | 3200 |

- [x] 同步調整新 POC 的瀏覽器與主機端網址。已更新 `app.py` 的 Agent UI CORS、README 的 Agent UI endpoint 設定步驟（`http://127.0.0.1:7877`）、LibreChat 的 `DOMAIN_CLIENT`／`DOMAIN_SERVER`，以及 Backstage 的 `app.baseUrl`、`backend.baseUrl` 和 CORS。保留 Backstage 容器監聽 `7007`，新 POC 主機入口使用 `7107`。
- [x] 更新 `integration/deploy.py` 健康檢查的 Backstage、Gateway 主機埠，並保留在 AgentOS 容器內探測 `127.0.0.1:7777`。`demo_run.py` 使用新 POC 的主機端點，容器內 `native_demo_run.py` 使用 `7777`。LibreChat Gateway 內部位址仍為 `http://agno-gateway:8080/v1`。
- [x] 確認所有 bind mounts 的解析路徑指向新 POC。靜態檢查確認容器只掛載新 POC 目錄或共用 `definitions/`、`scenarios/`、`benchmark/`；共用資料為唯讀。`integration/export_catalog.py` 會寫入新 POC 的 catalog 與 LibreChat 設定，部署快照及輸出也留在新 POC。
- [x] Compose project name 固定為 `agno-factory-tempo`，README 命令和 `integration/deploy.py` 內部呼叫均明確使用 `-p agno-factory-tempo`。新 POC 使用現有共用定義；會處理或寫入共用定義的舊 `bootstrap_definitions.py` 已移除。

## 3. 在新 POC 加入 Tempo 與 Grafana

- [x] 在新 Compose 移除複製來的 Langfuse Web、Worker、專用 PostgreSQL、ClickHouse、Redis、MinIO 與 init services，以及相關 volumes、環境變數和 `depends_on`。原 Compose 與 Langfuse 保留。
- [x] 新增 `observability/tempo.yaml`，以單機 `target=all` 啟動 Tempo。使用 `storage.trace.backend: local`，將 WAL 與 blocks 放在新 POC 的 `tempo_data` named volume，trace 保留 7 天。 [Tempo 部署規劃](https://grafana.com/docs/tempo/latest/set-up-for-tracing/setup-tempo/plan/) · [單機設定範例](https://grafana.com/docs/tempo/latest/set-up-for-tracing/setup-tempo/deploy/locally/linux/)
- [x] Docker Engine 啟動後確認 Tempo 容器可寫入 volume，並能啟動及持續保存 trace。Agent 與 Workflow trace 已由 Tempo API 查回；容器重建後仍可查詢另列於恢復驗收。
- [x] 在 Compose 網路內設定 Tempo OTLP/HTTP receiver `0.0.0.0:4318`。查詢 API 使用容器埠 `3200`，由主機端呼叫 `GET /ready` 確認就緒，查詢 API 可依 trace ID 取回 trace。Tempo 使用 distroless image，不在容器內設定需 shell／wget 的 healthcheck。映像固定為 Tempo `3.0.0`、Grafana `12.3.0`；API 實測列於驗收項目。 [Tempo HTTP API](https://grafana.com/docs/tempo/latest/api_docs/)
- [x] Docker Engine 啟動後驗證 Tempo/Grafana 容器掛載各自 named volume，且 Tempo 啟動成功、`/ready` 回傳 HTTP 200；已成功寫入並查回 trace、讀取 Grafana provisioned datasource。跨重建持久性另列於恢復驗收。
- [x] 新增 Grafana datasource provisioning，使用固定 UID `tempo`，由 Grafana 連到 `http://tempo:3200`。Grafana 使用獨立 `grafana_data` volume，管理員密碼由新 POC 的 `.env` 提供。 [Grafana Tempo datasource](https://grafana.com/docs/grafana/latest/datasources/tempo/configure-tempo-data-source/)

## 4. 接上 AgentOS 與示範流程

- [x] 調整新 `app.py`，使用 `AgnoInstrumentor` 與 OTLP/HTTP exporter。預設 endpoint 為 `http://tempo:4318/v1/traces`、service name 為 `agno-tempo-agentos`。已移除新 POC AgentOS 的 Langfuse Basic Auth 和 keys；AgentOS API 仍使用 `OS_SECURITY_KEY`。 [OTLP exporter 規格](https://opentelemetry.io/docs/specs/otel/protocol/exporter/)
- [x] 使用 `BatchSpanProcessor` 與有限匯出逾時。舊版 `factory_swarm.py` 未掛載到新 POC 容器且不列為支援入口；改以有 W3C context 的 AgentOS run 與 Workflow demos 驗證追蹤。Tempo 故障期間 run 是否照常完成列於待執行驗收。
- [x] 容器直接以 `uvicorn app:app` 啟動且停用 reload；`python app.py` 則直接交給 uvicorn app object，避免以 `__main__` 執行後又重複匯入 module 初始化 global OTel provider。
- [x] 套用新的單次 import 啟動方式重新建置 AgentOS image；74 個 lock constraints 使用既有建置快取。
- [x] 重建並重啟後確認 logs 僅有一次 OTel 初始化，無 TracerProvider 覆寫或重複 instrumentation。
- [x] 正常關閉 flush 與故障範圍已實測：Workflow 完成後立即停止 AgentOS，Tempo 仍查回該 run 的 trace；重啟 AgentOS 後 `/docs` HTTP 200、舊 trace 仍 HTTP 200。Tempo 停止期間的 3 筆新 Agent run 業務 PASS 但當時 trace 未驗證，報告已保留結果；Tempo 恢復後的新 Workflow trace 驗證通過。
- [x] 調整 `demo_run.py`，由新 POC `.env` 讀取 `TEMPO_QUERY_URL=http://127.0.0.1:3200` 與 AgentOS 主機端點；用有限重試查詢 trace，核對 W3C ingress、`openinference.span.kind`、Agent／LLM／Tool spans 與 `check_ticket_readiness` span。
- [x] 三情境 Agent demo 已確認每個 run 對應各自 trace ID，span 含 `check_ticket_readiness` 和 AGENT／LLM／TOOL kinds，parent ID 與送出的 W3C context 相符。
- [x] 確認 Agno run ID 與 session ID 的欄位及實際值：加入 AgentOS HTTP server span enrichment；實際 workflow response 的 `run_id`、`session_id` 與 Tempo `agno.run_id`、`agno.session_id` 完全一致，`session.id` 亦對應相同 session。
- [x] 調整 `native_demo_run.py`，保留 PAY-482 benchmark 格式並將 `poc` 欄位填為 `agno-tempo`；每個 Workflow run 透過 W3C `traceparent` 關聯 trace，輸出 trace ID、span 名稱／種類和驗證狀態。
- [x] Delivery-only Workflow 四情境執行成功、業務結果與 trace 全 verified；benchmark JSON 保留原格式並標示 `poc=agno-tempo`。ready trace 可查 Workflow、Team、平行 proposal／verification、Agent、LLM、Tool spans。
- [x] 執行包含 Continuous Improvement 的完整 demo；四個 Delivery 情境及 Improvement 均完成，5 筆 trace verified。改善 Workflow 為 COMPLETED、6 個 step results 成功；ready trace 含 Agent、LLM、Tool 與 parallel branches，benchmark 保留 4 個 case、`poc=agno-tempo` 及 run／trace 關聯欄位。
- [x] 在 AgentOS FastAPI app 啟用 FastAPI OpenTelemetry instrumentation；Agent 與 Workflow HTTP demo 均傳入各自 W3C `traceparent`，Tempo helper 以 trace ID 與遠端 parent span ID 核對 server span。
- [x] Docker Engine 可用後確認 ASGI server span、Workflow、Team 與平行分支的實際父子關係。ready trace 中 Workflow 的 parent 為 `POST /workflows/{workflow_id}/runs` server span，Parallel_Proposals／Parallel_Verification 分別包含各自子步驟。
- [x] 更新 `native_report.py`、`native_report_template.html` 與 Gateway 報告：以 AgentOS run 和 `step_results` 呈現步驟，列出 trace ID、驗證狀態、span 名稱／種類及 Grafana Explore 入口。缺 trace 時保留業務結果並標「未驗證」；空白或無效 JSON report input 也會產生空報告。
- [x] 建立 Tempo OTLP JSON 解析，正規化 `resourceSpans`／`scopeSpans`，解碼 base64 trace／parent span ID，供報告核對 trace 關聯及 span kind。
- [x] 檢查空資料與缺少 trace attributes：隔離的報告 fixture 產生空結果提示，缺 trace 時顯示「未驗證／尚無 trace ID」，沒有假設成功。
- [x] 清除新 POC 報告與文件中的舊 Langfuse trace ID、截圖和示範結果；目前報告列出 Trace ID、span 名稱／種類與 Grafana Explore 入口，不會把歷史資料當作新執行證據。
- [x] README 說明目前報告只列 trace ID、span 名稱與種類，不重製 Langfuse 的圖形、成本或 token 儀表板；未實測的欄位清楚標示尚未驗證。
- [x] Docker Engine 可用後實測輸入輸出、token、耗時及成本欄位的實際可見性，並依結果更新 README。Tempo LLM spans 有 model、prompt/completion/total/cache token 欄位及開始／結束時間；未提供 cost 欄位，README 已說明目前不顯示費用。
- [x] `demo_run.py` 在 Tempo 查詢失敗或逾時時仍寫出已完成的業務結果與「追蹤未驗證」報告。保留業務或 trace 驗證失敗時的非零結束碼；讀不到 Tempo trace 會回傳空 spans 並產生報告。
- [x] 處理 `factory_swarm.py` 的既有相依。來源程式依賴不存在的 `swarm_report_template.html`，且不是目前 AgentOS definitions 的支援入口；已從新 POC 移除舊 CLI 及只供該 CLI 使用的 `integration/bootstrap_definitions.py`。新 POC 支援入口為 `demo_run.py` 與 `native_demo_run.py`。
- [x] 更新新 POC 的 README、`integration/README.md` 及 `integration/export_catalog.py`。已說明獨立 project、初始化、建置、啟動、PAY-482、Grafana 查 span、Workflow 報告、definition deploy 與停止方式；catalog 說明指向 Grafana Tempo。
- [x] Docker Engine 可用後實際執行兩個 demo，並保存本次 Tempo POC 產生的 Agent 與 Workflow 報告作為示範證據：`demo-results.json`／`demo-report.html`、`native-results.json`／`native-report.html` 和 benchmark 均已產生。

## 5. 僅在驗收要求 S3 相容儲存時加入 MinIO

預設的單機 POC 採第 3 節的 `local` 儲存，不需 MinIO。只有驗收要求 Tempo 使用 S3 API 時，才將下列項目納入範圍。 [Tempo 儲存設定](https://grafana.com/docs/tempo/latest/configuration/)

- [x] 本次 POC 採 local backend；S3／MinIO 設定與 bucket 驗收不在目前範圍，除非後續驗收明確要求 S3。

- [x] (N/A) 本次採用 Tempo local backend，沒有新增 Tempo 專用 MinIO；原 POC Langfuse 繼續使用自己的 MinIO。
- [x] (N/A) S3 backend／MinIO endpoint 與 bucket 驗收僅在未來明確要求 S3 時實作；目前 local named-volume trace 已通過重建驗收。
- [x] (N/A) 不需要 S3 bucket 寫入／重建驗收；Tempo local backend 的持久性已由 named volume down/up 與查回 trace 驗證。

## 6. 驗收 Checklist

以下新 POC 指令均從 `pocs/agno-tempo/` 執行。Agent、Delivery、完整 Workflow、Tempo trace、Gateway、Agent UI、部署、故障恢復、兩 POC 並行與獨立停止均已驗收；12 個回歸 tests 通過。剩餘只有 Grafana Explore／LibreChat 登入後的手動 GUI 檢視。原 POC 主機端 `127.0.0.1:7777` reset，容器內 API 與 Langfuse 正常，詳見並行驗收項。

- [x] **靜態設定**　`docker compose -p agno-factory-tempo config --quiet` 通過。解析出的服務清單含 `tempo`、`grafana`，不含 Langfuse／MinIO；Compose volume aliases 獨立。
- [x] **Image build**　`docker compose -p agno-factory-tempo build agentos backstage agent-ui` 成功；Backstage Yarn 顯示 peer dependency warnings，production build 仍完成。
- [x] **Compose 啟動**　`docker compose -p agno-factory-tempo up -d` 成功；專案專用 network、8 個 named volumes 均建立，`catalog-export` exit 0，所有服務容器進入 running。
- [x] **服務就緒**　Tempo `/ready`、Grafana `/api/health`、AgentOS `/docs`、Agent UI、Backstage root／guest auth、LibreChat、Grafana Tempo datasource 及 Gateway `/v1/models` 均回 HTTP 200；Gateway 列出 29 個模型。
- [x] **Agent 業務情境**　`python demo_run.py` 的 `stale` → `NOT READY`、`passed` → `READY`、`timeout` → `UNKNOWN` 均通過；重跑後三筆 Tempo trace 皆 verified，`agno.run_id` 與實際 AgentOS run ID 相符，並產生 JSON／HTML 結果。
- [x] 受控 AgentOS 請求確認 Tempo server span 的 `parentSpanId` 等於送出的 W3C parent ID；定位到查詢 helper 曾在任何 spans 到達時就提前返回。
- [x] `tempo_traces.read_trace()` 改為等待 server span 到達且 span ID 集合穩定 1.5 秒後再回傳，避免把初始部分 trace 當成完整 trace。
- [x] 重跑三種 PAY-482 情境，parent ID、Agent／LLM／Tool trace 驗證全數通過，`demo_run.py` exit 0。
- [x] Tempo API trace 已確認 ASGI／Workflow／parallel／Agent／LLM／Tool 階層；Agent UI 實際請求回 `READY` 並在 Tempo 查到 trace，Gateway chat-completion 請求亦取得唯一 trace。
- [ ] 登入後手動檢視 Grafana Explore 與 LibreChat 對話畫面。Tempo／Grafana datasource API、Gateway 和兩條入口 trace 已通過；瀏覽器中的 Grafana Explore 導向 `/login`。`computer-use` skill 明確禁止自動化使用者認證對話框，因此本次保留為手動項目。
- [x] Agent UI endpoint 已設為 `http://127.0.0.1:7877`，使用映像提供的既有 auth token 後連線成功；UI 實際請求回 `READY`，Tempo 依 UI session ID 查得 Agent trace。其 SSE run path 已補標 `agno.run_id`／`agno.session_id`，並以同一 session 的串流請求核對兩個欄位。
- [x] LibreChat 所設定的 OpenAI 相容 Gateway 已實際收取 chat-completion 請求並回 HTTP 200；Tempo 找到唯一 session trace，AgentOS run／session IDs 與 `agno.run_id`／`agno.session_id` 相符。瀏覽器端 LibreChat 與 Grafana Explore 尚未手動登入檢視。
- [x] **Delivery Workflow 與 benchmark**　`native_demo_run.py --delivery-only` 四案均 PASS、trace verified，預期狀態與 `released=false` 已由 runner 核對；benchmark 有 4 案且 `poc=agno-tempo`。Tempo ready trace 可查 Software_Delivery、Team、Parallel_Proposals、Parallel_Verification、Agent、LLM、Tool spans。
- [x] **Continuous Improvement**　完整示範四個 Delivery 案及 Improvement；5 筆 trace verified，改善 Workflow 完成 6 步驟。`benchmark-results.json` 有 4 案並保留 `poc=agno-tempo`。
- [x] **報告與定義部署**　`native_report.py` 已執行，Gateway `/report` HTTP 200 且含 5 筆 Workflow trace、Grafana 入口與 Improvement 結果。`integration/deploy.py deploy` 部署 revision `4de47f618e205ed9`，AgentOS／Gateway／Backstage health 一致；LibreChat 回 HTTP 200，Gateway 列出 29 個 model IDs，Backstage catalog revision 驗證通過。`status` 顯示 revision active。
- [x] **Definitions 靜態驗證**　`python integration/deploy.py validate` 通過；根目錄共用定義可供新 POC 載入（revision `4de47f618e205ed9`，26 agents、3 teams、14 skills、2 workflows）。Python demo、report、deployment、catalog exporter 與 Gateway 檔案通過 `py_compile`。
- [x] **部署隔離**　在新 POC 執行 `python integration/deploy.py deploy`、`status`，確認只重建明確列出的 `agno-factory-tempo` AgentOS／Gateway／LibreChat／Backstage 服務，revision、Backstage catalog 和 Gateway 清單一致。這是第一個 release，沒有 previous revision，rollback 條件不成立。
- [x] 比較兩套 deployment markers（原 `bdcc8db58b2161b3`、Tempo `4de47f618e205ed9`）、catalog、LibreChat config、容器、volume alias、ports 與 `swarm-output/` 路徑：全部位於各自 POC/project；兩套同時運作且資料不共用。原 LibreChat tracked config 已還原至啟動前內容。
- [x] 同一 session 的跨 run 關聯不交叉：三個 Agent runs 共用一個 `session.id`、兩個 Workflow runs 共用另一個 `session.id`；每次 run 的 `agno.run_id`／trace ID 唯一且相符。
- [x] **追蹤與報告邊界**　成功、NOT READY／UNKNOWN、平行分支、缺 trace 屬性提示均已核對；Tempo 停止期間 3 個 business results 保留、trace 標「未驗證」，runner 以非零碼回報。Tempo 恢復後新 run 的 trace 查詢及 run ID 對應通過。
- [x] **回歸測試**　容器執行 `test_native_workflows`、`test_payment_demo` 共 8 tests 通過；主機 `integration.test_registry` 共 4 tests 通過。
- [x] Tempo 使用同一個 `tempo_data` named volume force-recreate 後，`/ready` HTTP 200；重建前的 Workflow、Gateway trace 仍可由 trace ID 以 HTTP 200 查回。
- [x] **故障恢復**　暫停 Tempo 時三個 Agent run 均完成且業務 PASS；demo JSON／HTML 保留結果並標示 trace 未驗證，程式以非零碼回報 trace 驗證失敗。恢復 Tempo 後 `/ready` HTTP 200，新 AgentOS run 完成且 run ID／trace 驗證通過。
- [x] 原 Agno／Langfuse 與新 Agno／Tempo 已同時啟動。projects、network、主機埠與 volumes 分離：原 POC 使用 `agno-factory-local_*` 與 3001／7777／7778 等埠，新 POC 使用 `agno-factory-tempo_*` 與 3002／7877／7878 等埠。
- [x] 各跑一筆 PAY-482，分別確認新 POC trace 到 Tempo、原 POC trace 到 Langfuse；兩個輸出目錄分別位於 `pocs/agno/swarm-output/` 與 `pocs/agno-tempo/swarm-output/`。原 POC 的主機端 `demo_run.py` 受 7777 port reset 阻擋；改由原 AgentOS 容器內部執行，Workflow 完成且 Langfuse API 用相同 trace ID 查回 7 個 spans。原 POC 檔案未修改。
- [x] `docker compose -p agno-factory-tempo down` 只停止新 POC；原 AgentOS 容器內 `/docs` 仍回 HTTP 200，既有 Langfuse trace 仍以 HTTP 200 查回且含 7 spans。
- [x] 以 `docker compose -p agno-factory-tempo up -d --no-build` 重啟新 POC；Tempo `/ready`、Gateway `/report` 均回 HTTP 200，重啟前 trace `4f0e7ce929ee6f0381ae4c8456385aaf` 仍可從原 named volume 查回。原 Agno／Langfuse 服務仍在運作。

# Agno Tempo POC：Catalog、LibreChat 與定義部署

本目錄的部署與 Gateway 指令只操作 Compose project agno-factory-tempo。請先切換至 pocs/agno-tempo/，不要從 pocs/agno/ 執行。

## 啟動服務

在新 POC 根目錄初始化 .env 並設定模型憑證，再執行：

\`\`\`powershell
python integration/setup_env.py
docker compose -p agno-factory-tempo config --quiet
docker compose -p agno-factory-tempo up -d --build
\`\`\`

catalog-export 會使用 repository 共用 definitions/，並在本 POC 產生 integration/catalog/ 與 integration/librechat.yaml。這些生成檔、deployment 快照與 swarm-output/ 僅屬於新 POC，並由根目錄 .gitignore 排除。

## 驗證與部署 definitions

\`\`\`powershell
python integration/deploy.py validate
python integration/deploy.py deploy
python integration/deploy.py status
\`\`\`

deploy 會複製共用 definitions 到本目錄 deployment/releases/，再更新本 POC AgentOS、Gateway、LibreChat 與 Backstage。回復上一版本可執行 python integration/deploy.py rollback。所有腳本內的 Compose 呼叫均明確使用 -p agno-factory-tempo。舊版 integration/bootstrap_definitions.py 已從新 POC 移除，definitions/ 僅供唯讀共用。

## 入口和追蹤

- LibreChat：http://127.0.0.1:3090
- Backstage：http://127.0.0.1:7107
- Gateway 報告：http://127.0.0.1:7878/report
- Grafana Explore：http://127.0.0.1:3002/explore
- Tempo readiness：http://127.0.0.1:3200/ready

Gateway 將 LibreChat 的 Agent/Team 請求轉送至 AgentOS。AgentOS 以 OTLP/HTTP 將 traces 傳到 Compose 網路內的 Tempo。Catalog 關係是由定義推導的靜態關係；實際執行委派與耗時請查看 Grafana Tempo trace。報告先由 AgentOS Workflow demo 產生，包含 run 與 trace 對照。

以 Ctrl+C 或 docker compose -p agno-factory-tempo down 停止本 POC，不會停止原本的 Agno／Langfuse POC。


# AgentOS API 契約快照（目前部署：3.2.1）

最後更新：2026-11-23（台灣時間）。本文件保留 2026-11-21 Agno 2.9.0 的歷史 OpenAPI inventory，並以 Docker 重啟後執行中的 Agno 3.2.1 AgentOS 為目前契約。Live API check 在 Docker 容器與本機 Agent UI 執行；只記路由中繼資料、狀態與欄位名稱，不存憑證、prompt 或原始設定。

## 快照摘要

- **目前 runtime：** Agno 3.2.1；OpenAPI 3.1.0；94 paths、135 HTTP operations（含本機 Factory `/factory/catalog` extension）。
- **歷史基線：** Agno 2.9.0；OpenAPI 1.0.0；75 paths、112 HTTP operations。後續路由 inventory 僅供 v2 比較，不能代表目前部署。
- 3.2.1 live 全部 135 個 operation 的 route、parameters、schema refs 與 OpenAPI security 宣告另見[目前版 operation inventory](agentos-api-openapi-3.2.1.md)。此 runtime 快照包含 POC 本機 Factory extension，不能當作上游 AgentOS package 的原生路由清單。
- Security schemes：HTTPBearer。Agno runtime 仍可能以 middleware 保護未在 operation 上宣告 security 的路由；下表的 OpenAPI 欄位不取代實際 HTTP 驗證。
- AgentOS 使用 PostgresDb，compose 掛載 Factory definitions；POC Langfuse OTel exporter 已啟動。
- 對照功能代碼：F02 對話 · F03 Agents · F04 Teams · F05 Workflows · F07 Sessions/Runs · F09 Knowledge · F10 Memory/Learnings · F11 Traces · F12 Metrics · F13 Evaluations · F14 Approvals · F15 Schedules · F16 System。各頁完整規格見 agent-ui-capability-plan.md。

## 3.2.1 live contract checks

| Request | Result | Confirmed contract |
|---|---:|---|
| `GET /health` | 200 in the deployed UI | AgentOS health is `OK`. |
| `GET /info` | 200 | `agno_version` is `3.2.1`; System Explorer displays this runtime value. |
| `GET /config` | 200 | `available_models` contains 1 safe model summary; the v3 UI reads models from this field. |
| `GET /models` | 404 | This v3 deployment does not expose the v2 route. The UI keeps `/models` only as a compatibility fallback for older AgentOS versions. |
| `GET /factory/revision` | 200 | Factory revision `bdcc8db58b2161b3`; counts are 26 agents, 3 teams, 2 workflows. |
| `GET /factory/catalog` | 200 with the local Agent UI token; 401 without Authorization | Returns the complete Factory skill snapshot, revision, scope, and each Skill's referencing Agent IDs/names. The operation has no OpenAPI `security` declaration, but live AgentOS middleware still enforces Bearer auth. |
| `GET /openapi.json` | 200 | OpenAPI 3.1.0; 94 paths and 135 HTTP operations, including the local Factory catalog extension. |
| `GET /sessions/{session_id}/compactions` for an existing Workflow session | 200 | Response is an empty JSON array (`0` records), a successful empty state rather than an error. |

## 3.2.1 targeted read-only GET audit (2026-11-22)

This audit supplements the OpenAPI inventory with observed runtime status. Requests were GET-only; no prompt, record content, credentials, or raw error detail was saved.

| Scope | Request(s) | Result |
|---|---|---|
| No Authorization | `/health` | 200. |
| No Authorization | `/config`, `/agents`, `/factory/revision`, `/factory/catalog`, `/approvals`, `/components`, `/queue`, `/schedules`, `/service-accounts` | 401 on each route. The in-app Overview also showed successful health/runtime sources beside independent 401/Retry cards for Factory revision, sessions, and config. |
| Authenticated core and catalog reads | `/config`, `/info`, `/factory/revision`, `/factory/catalog` | 200; one available model, runtime counts of 26 Agents/3 Teams/2 Workflows, and 14 Skills. |
| Authenticated component reads | `/agents`, `/teams`, `/workflows` and sampled runtime/Factory detail routes | 200; 26 Agents, 3 Teams, 2 Workflows; sampled Team detail had 2 members, Workflow detail had 6 steps, and Factory Agent detail had 1 Skill. |
| Sessions and schemas | `/sessions?limit=1&page=1`, `/sessions/filter-schema`, `/traces/filter-schema` | 200; 1 session, 9 session filter fields, 13 trace filter fields. The existing Workflow session compactions route returned 200 with 0 records. |
| Memory and Learnings | `/memories`, `/learnings`, `/learnings/users`, `/user_memory_stats` with the selected DB; `/memory_topics` | 200; record/stat lists were empty. |
| Knowledge | `/knowledge/config` and `/knowledge/content` without `db_id`; both routes with the selected DB | Without `db_id`: 503. With the selected DB: 404, consistent with no configured Knowledge instance. No content or search result was available. |
| Traces and evaluations | `/traces`, `/trace_session_stats`, `/eval-runs?limit=10&page=1` | 200; each list was empty. The eval response meta was page 1, limit 10, total_pages 0, total_count 0. This does not establish non-empty trace detail, eval-run detail, or write behavior. |
| Registry pagination | `/registry` default page; `/registry?limit=3&page=2`; `/registry?limit=2&page=1` | 200; 20 items on the default page, 3 on page 2, and page 1 metadata reports `total_pages=35`, `total_count=69`. A read-only aggregate over the 69 rows counted 26 agents, 3 teams, 2 workflows, 27 tools, 9 functions, 1 model, and 1 db; names, IDs, and metadata values were not retained. |
| Metrics status | `/metrics` with selected DB/date range; `/metrics/refresh/status`, `/os/metrics/refresh/status` | 200; legacy metrics returned 2 rows and both refresh-status routes responded. No refresh operation was triggered. |
| Configuration-dependent management reads | `/approvals`, `/components`, `/queue`, `/schedules`, `/service-accounts` with Authorization | 503 on each, with a `detail` field classified as configuration-dependent. These are not successful empty lists and no management UI/data was verified. |

The audit covers selected read operations, not every OpenAPI operation or every schema instance. Disabled/write operations, untested query combinations, and operations that could create data or run a model remain outside this read-only pass.

The v3 `CompactionSchema` fields are `id`, `run_id`, `messages_compacted`, `tokens_before`, `tokens_after`, `created_at`, and `archived`. This endpoint exposes compaction metadata only; the current response does not provide a summary or archived messages. The UI does not invent either field.

The local `GET /factory/catalog` extension is served by this POC's AgentOS application, not by the upstream Agno 3.2.1 package contract. It returns `revision`, a `scope` label, and every Factory Skill definition with its `agents` reverse references. The browser read returned 14 Skills from the complete snapshot. Skill instructions are returned only after AgentOS Bearer authorization; a Docker-side request without Authorization returned HTTP 401.

The System Explorer browser check used the in-app Agent UI with the user-provided token already entered. It showed health `OK`, Agno `3.2.1`, 26 Agents, 3 Teams, 2 Workflows, 1 session DB, 1 available model, and a Factory revision whose counts match AgentOS. The token remained masked. See [3.2.1 UI verification](agent-ui-verification-evidence.md#agno-321-ui-verification).

## Historical OpenAPI operation inventory (Agno 2.9.0)

Params 列出 query/path/header 參數名稱；Request 與 Response 優先記錄 OpenAPI $ref。內嵌 schema 未強行展平，詳細欄位可在本機 http://localhost:7777/openapi.json 查閱。OpenAPI security 只記錄 spec 宣告，實際 auth 以 live 401/200 測試為準。

| Method | Path | operationId | Tags | Params | Request | Response | Security | 規劃歸屬 |
|---|---|---|---|---|---|---|---|---|
| GET | / | get_api_info | Home | — | — | inline / unspecified | No operation security declared; runtime auth still verify | F02/F16 or runtime utility |
| GET | /health | health_check | Health | — | — | #/components/schemas/HealthResponse | No operation security declared; runtime auth still verify | F17 System |
| GET | /info | get_info | Core | — | — | #/components/schemas/InfoResponse | No operation security declared; runtime auth still verify | F17 System |
| GET | /config | get_config | Core | — | — | #/components/schemas/ConfigResponse | OpenAPI security declared | F17 System |
| GET | /models | get_models | Core | — | — | inline / unspecified | OpenAPI security declared | F02/F16 or runtime utility |
| POST | /agents/{agent_id}/runs | create_agent_run | Agents | agent_id | #/components/schemas/Body_create_agent_run | inline / unspecified | OpenAPI security declared | F03 Agents |
| GET | /agents/{agent_id}/runs | list_agent_runs | Agents | agent_id, session_id, status | — | inline / unspecified | OpenAPI security declared | F03 Agents |
| POST | /agents/{agent_id}/runs/{run_id}/cancel | cancel_agent_run | Agents | agent_id, run_id, session_id | — | inline / unspecified | OpenAPI security declared | F03 Agents |
| POST | /agents/{agent_id}/runs/{run_id}/continue | continue_agent_run | Agents | agent_id, run_id | #/components/schemas/Body_continue_agent_run | inline / unspecified | OpenAPI security declared | F03 Agents |
| POST | /agents/{agent_id}/sessions/{session_id}/fork | fork_agent_session | Agents | agent_id, session_id, user_id | — | inline / unspecified | OpenAPI security declared | F03 Agents |
| GET | /agents | get_agents | Agents | — | — | inline / unspecified | OpenAPI security declared | F03 Agents |
| GET | /agents/{agent_id} | get_agent | Agents | agent_id | — | #/components/schemas/AgentResponse | OpenAPI security declared | F03 Agents |
| GET | /agents/{agent_id}/runs/{run_id} | get_agent_run | Agents | agent_id, run_id, session_id | — | inline / unspecified | OpenAPI security declared | F03 Agents |
| GET | /agents/{agent_id}/runs/{run_id}/checkpoints | list_agent_run_checkpoints | Agents | agent_id, run_id, session_id | — | inline / unspecified | OpenAPI security declared | F03 Agents |
| GET | /agents/{agent_id}/runs/{run_id}/checkpoints/{message_index} | get_agent_run_checkpoint_snapshot | Agents | agent_id, run_id, message_index, session_id | — | inline / unspecified | OpenAPI security declared | F03 Agents |
| POST | /agents/{agent_id}/runs/{run_id}/resume | resume_agent_run_stream | Agents | agent_id, run_id | #/components/schemas/Body_resume_agent_run_stream | inline / unspecified | OpenAPI security declared | F03 Agents |
| POST | /teams/{team_id}/runs | create_team_run | Teams | team_id | #/components/schemas/Body_create_team_run | inline / unspecified | OpenAPI security declared | F04 Teams |
| GET | /teams/{team_id}/runs | list_team_runs | Teams | team_id, session_id, status | — | inline / unspecified | OpenAPI security declared | F04 Teams |
| POST | /teams/{team_id}/runs/{run_id}/cancel | cancel_team_run | Teams | team_id, run_id, session_id | — | inline / unspecified | OpenAPI security declared | F04 Teams |
| POST | /teams/{team_id}/runs/{run_id}/resume | resume_team_run_stream | Teams | team_id, run_id | #/components/schemas/Body_resume_team_run_stream | inline / unspecified | OpenAPI security declared | F04 Teams |
| POST | /teams/{team_id}/runs/{run_id}/continue | continue_team_run | Teams | team_id, run_id | #/components/schemas/Body_continue_team_run | inline / unspecified | OpenAPI security declared | F04 Teams |
| POST | /teams/{team_id}/sessions/{session_id}/fork | fork_team_session | Teams | team_id, session_id, user_id | — | inline / unspecified | OpenAPI security declared | F04 Teams |
| GET | /teams | get_teams | Teams | — | — | inline / unspecified | OpenAPI security declared | F04 Teams |
| GET | /teams/{team_id} | get_team | Teams | team_id | — | #/components/schemas/TeamResponse | OpenAPI security declared | F04 Teams |
| GET | /teams/{team_id}/runs/{run_id} | get_team_run | Teams | team_id, run_id, session_id | — | inline / unspecified | OpenAPI security declared | F04 Teams |
| GET | /teams/{team_id}/runs/{run_id}/checkpoints | list_team_run_checkpoints | Teams | team_id, run_id, session_id | — | inline / unspecified | OpenAPI security declared | F04 Teams |
| GET | /teams/{team_id}/runs/{run_id}/checkpoints/{message_index} | get_team_run_checkpoint_snapshot | Teams | team_id, run_id, message_index, session_id | — | inline / unspecified | OpenAPI security declared | F04 Teams |
| GET | /workflows | get_workflows | Workflows | — | — | inline / unspecified | OpenAPI security declared | F05/F07/F08 Workflows |
| GET | /workflows/{workflow_id} | get_workflow | Workflows | workflow_id, version | — | #/components/schemas/WorkflowResponse | OpenAPI security declared | F05/F07/F08 Workflows |
| POST | /workflows/{workflow_id}/runs | create_workflow_run | Workflows | workflow_id | #/components/schemas/Body_create_workflow_run | inline / unspecified | OpenAPI security declared | F05/F07/F08 Workflows |
| GET | /workflows/{workflow_id}/runs | list_workflow_runs | Workflows | workflow_id, session_id, status, factory_input | — | inline / unspecified | OpenAPI security declared | F05/F07/F08 Workflows |
| POST | /workflows/{workflow_id}/runs/{run_id}/continue | continue_workflow_run | Workflows | workflow_id, run_id | #/components/schemas/Body_continue_workflow_run | inline / unspecified | OpenAPI security declared | F05/F07/F08 Workflows |
| POST | /workflows/{workflow_id}/runs/{run_id}/cancel | cancel_workflow_run | Workflows | workflow_id, run_id, session_id | — | inline / unspecified | OpenAPI security declared | F05/F07/F08 Workflows |
| POST | /workflows/{workflow_id}/runs/{run_id}/resume | resume_workflow_run_stream | Workflows | workflow_id, run_id | #/components/schemas/Body_resume_workflow_run_stream | inline / unspecified | OpenAPI security declared | F05/F07/F08 Workflows |
| GET | /workflows/{workflow_id}/runs/{run_id} | get_workflow_run | Workflows | workflow_id, run_id, session_id, factory_input | — | inline / unspecified | OpenAPI security declared | F05/F07/F08 Workflows |
| GET | /sessions | get_sessions | Sessions | type, component_id, user_id, session_name, limit, page, sort_by, sort_order, db_id, table | — | #/components/schemas/PaginatedResponse_SessionSchema_ | OpenAPI security declared | F07 Sessions/Runs |
| POST | /sessions | create_session | Sessions | type, db_id | #/components/schemas/CreateSessionRequest | inline / unspecified | OpenAPI security declared | F07 Sessions/Runs |
| DELETE | /sessions | delete_sessions | Sessions | user_id, db_id, table | #/components/schemas/DeleteSessionRequest | inline / unspecified | OpenAPI security declared | F07 Sessions/Runs |
| GET | /sessions/{session_id} | get_session_by_id | Sessions | session_id, type, user_id, db_id, table | — | inline / unspecified | OpenAPI security declared | F07 Sessions/Runs |
| DELETE | /sessions/{session_id} | delete_session | Sessions | session_id, user_id, db_id, table | — | inline / unspecified | OpenAPI security declared | F07 Sessions/Runs |
| PATCH | /sessions/{session_id} | update_session | Sessions | session_id, type, user_id, db_id, table | #/components/schemas/UpdateSessionRequest | inline / unspecified | OpenAPI security declared | F07 Sessions/Runs |
| GET | /sessions/{session_id}/runs | get_session_runs | Sessions | session_id, type, user_id, created_after, created_before, status, db_id, table | — | inline / unspecified | OpenAPI security declared | F07 Sessions/Runs |
| GET | /sessions/{session_id}/runs/{run_id} | get_session_run | Sessions | session_id, run_id, type, user_id, db_id, table | — | inline / unspecified | OpenAPI security declared | F07 Sessions/Runs |
| POST | /sessions/{session_id}/rename | rename_session | Sessions | session_id, type, user_id, db_id, table | #/components/schemas/Body_rename_session | inline / unspecified | OpenAPI security declared | F07 Sessions/Runs |
| POST | /memories | create_memory | Memory | db_id, table | #/components/schemas/UserMemoryCreateSchema | #/components/schemas/UserMemorySchema | OpenAPI security declared | F10 Memory/Learnings |
| DELETE | /memories | delete_memories | Memory | db_id, table | #/components/schemas/DeleteMemoriesRequest | inline / unspecified | OpenAPI security declared | F10 Memory/Learnings |
| GET | /memories | get_memories | Memory | user_id, agent_id, team_id, search_content, limit, page, sort_by, sort_order, db_id, table, topics | — | #/components/schemas/PaginatedResponse_UserMemorySchema_ | OpenAPI security declared | F10 Memory/Learnings |
| DELETE | /memories/{memory_id} | delete_memory | Memory | memory_id, user_id, db_id, table | — | inline / unspecified | OpenAPI security declared | F10 Memory/Learnings |
| GET | /memories/{memory_id} | get_memory | Memory | memory_id, user_id, db_id, table | — | #/components/schemas/UserMemorySchema | OpenAPI security declared | F10 Memory/Learnings |
| PATCH | /memories/{memory_id} | update_memory | Memory | memory_id, db_id, table | #/components/schemas/UserMemoryCreateSchema | #/components/schemas/UserMemorySchema | OpenAPI security declared | F10 Memory/Learnings |
| GET | /memory_topics | get_memory_topics | Memory | user_id, db_id, table | — | inline / unspecified | OpenAPI security declared | F02/F16 or runtime utility |
| GET | /user_memory_stats | get_user_memory_stats | Memory | limit, page, user_id, db_id, table | — | #/components/schemas/PaginatedResponse_UserStatsSchema_ | OpenAPI security declared | F02/F16 or runtime utility |
| POST | /optimize-memories | optimize_memories | Memory | db_id, table | #/components/schemas/OptimizeMemoriesRequest | #/components/schemas/OptimizeMemoriesResponse | OpenAPI security declared | F02/F16 or runtime utility |
| GET | /learnings | list_learnings | Learnings | learning_type, user_id, agent_id, team_id, session_id, namespace, entity_id, entity_type, limit, page, sort_by, sort_order, db_id, table | — | #/components/schemas/PaginatedResponse_LearningResponse_ | OpenAPI security declared | F10 Memory/Learnings |
| POST | /learnings | create_learning | Learnings | db_id, table | #/components/schemas/LearningCreate | #/components/schemas/LearningResponse | OpenAPI security declared | F10 Memory/Learnings |
| GET | /learnings/users | list_learning_users | Learnings | learning_type, user_id, limit, page, sort_by, sort_order, db_id, table | — | #/components/schemas/PaginatedResponse_LearningUserStats_ | OpenAPI security declared | F10 Memory/Learnings |
| DELETE | /learnings/users/{user_id} | delete_learning_user | Learnings | user_id, learning_type, db_id, table | — | inline / unspecified | OpenAPI security declared | F10 Memory/Learnings |
| GET | /learnings/{learning_id} | get_learning | Learnings | learning_id, db_id, table | — | #/components/schemas/LearningResponse | OpenAPI security declared | F10 Memory/Learnings |
| PATCH | /learnings/{learning_id} | update_learning | Learnings | learning_id, db_id, table | #/components/schemas/LearningUpdate | #/components/schemas/LearningResponse | OpenAPI security declared | F10 Memory/Learnings |
| DELETE | /learnings/{learning_id} | delete_learning | Learnings | learning_id, db_id, table | — | inline / unspecified | OpenAPI security declared | F10 Memory/Learnings |
| GET | /eval-runs | get_eval_runs | Evals | agent_id, team_id, workflow_id, model_id, type, limit, page, sort_by, sort_order, db_id, table, eval_types | — | #/components/schemas/PaginatedResponse_EvalSchema_ | OpenAPI security declared | F13 Evaluations |
| DELETE | /eval-runs | delete_eval_runs | Evals | db_id, table | #/components/schemas/DeleteEvalRunsRequest | inline / unspecified | OpenAPI security declared | F13 Evaluations |
| POST | /eval-runs | run_eval | Evals | db_id, table | #/components/schemas/EvalRunInput | #/components/schemas/EvalSchema | OpenAPI security declared | F13 Evaluations |
| GET | /eval-runs/{eval_run_id} | get_eval_run | Evals | eval_run_id, db_id, table | — | #/components/schemas/EvalSchema | OpenAPI security declared | F13 Evaluations |
| PATCH | /eval-runs/{eval_run_id} | update_eval_run | Evals | eval_run_id, db_id, table | #/components/schemas/UpdateEvalRunRequest | #/components/schemas/EvalSchema | OpenAPI security declared | F13 Evaluations |
| GET | /metrics | get_metrics | Metrics | starting_date, ending_date, db_id, table | — | #/components/schemas/MetricsResponse | OpenAPI security declared | F12 Metrics |
| POST | /metrics/refresh | refresh_metrics | Metrics | db_id, table, background | — | inline / unspecified | OpenAPI security declared | F12 Metrics |
| GET | /metrics/refresh/status | get_metrics_refresh_status | Metrics | db_id, table | — | #/components/schemas/MetricsRefreshStatusResponse | OpenAPI security declared | F12 Metrics |
| POST | /knowledge/content | upload_content | Knowledge | db_id, knowledge_id | #/components/schemas/Body_upload_content | inline / unspecified | OpenAPI security declared | F09 Knowledge |
| GET | /knowledge/content | get_content | Knowledge | limit, page, sort_by, sort_order, db_id, knowledge_id | — | #/components/schemas/PaginatedResponse_ContentResponseSchema_ | OpenAPI security declared | F09 Knowledge |
| DELETE | /knowledge/content | delete_all_content | Knowledge | db_id, knowledge_id | — | inline / unspecified | OpenAPI security declared | F09 Knowledge |
| POST | /knowledge/remote-content | upload_remote_content | Knowledge | db_id, knowledge_id | #/components/schemas/Body_upload_remote_content | inline / unspecified | OpenAPI security declared | F09 Knowledge |
| PATCH | /knowledge/content/{content_id} | update_content | Knowledge | content_id, db_id, knowledge_id | #/components/schemas/Body_update_content | #/components/schemas/ContentResponseSchema | OpenAPI security declared | F09 Knowledge |
| GET | /knowledge/content/{content_id} | get_content_by_id | Knowledge | content_id, db_id, knowledge_id | — | #/components/schemas/ContentResponseSchema | OpenAPI security declared | F09 Knowledge |
| DELETE | /knowledge/content/{content_id} | delete_content_by_id | Knowledge | content_id, db_id, knowledge_id | — | #/components/schemas/ContentResponseSchema | OpenAPI security declared | F09 Knowledge |
| GET | /knowledge/content/{content_id}/status | get_content_status | Knowledge | content_id, db_id, knowledge_id | — | #/components/schemas/ContentStatusResponse | OpenAPI security declared | F09 Knowledge |
| POST | /knowledge/search | search_knowledge | Knowledge | — | #/components/schemas/VectorSearchRequestSchema | #/components/schemas/PaginatedResponse_VectorSearchResult_ | OpenAPI security declared | F09 Knowledge |
| GET | /knowledge/config | get_knowledge_config | Knowledge | db_id, knowledge_id | — | #/components/schemas/ConfigResponseSchema | OpenAPI security declared | F09 Knowledge |
| GET | /knowledge/{knowledge_id}/sources | list_content_sources | Knowledge | knowledge_id, db_id | — | inline / unspecified | OpenAPI security declared | F09 Knowledge |
| GET | /knowledge/{knowledge_id}/sources/{source_id}/files | list_source_files | Knowledge | knowledge_id, source_id, prefix, limit, page, delimiter, db_id | — | #/components/schemas/SourceFilesResponseSchema | OpenAPI security declared | F09 Knowledge |
| GET | /traces | get_traces | Traces, Traces | run_id, session_id, user_id, agent_id, team_id, workflow_id, status, start_time, end_time, page, limit, db_id | — | #/components/schemas/PaginatedResponse_TraceSummary_ | OpenAPI security declared | F11 Traces |
| GET | /traces/filter-schema | get_traces_filter_schema | Traces, Traces | — | — | #/components/schemas/FilterSchemaResponse | OpenAPI security declared | F11 Traces |
| GET | /traces/{trace_id} | get_trace | Traces, Traces | trace_id, span_id, run_id, db_id | — | inline / unspecified | OpenAPI security declared | F11 Traces |
| GET | /trace_session_stats | get_trace_stats | Traces, Traces | user_id, agent_id, team_id, workflow_id, start_time, end_time, page, limit, db_id | — | #/components/schemas/PaginatedResponse_TraceSessionStats_ | OpenAPI security declared | F02/F16 or runtime utility |
| POST | /traces/search | search_traces | Traces, Traces | db_id | #/components/schemas/TraceSearchRequest | inline / unspecified | OpenAPI security declared | F11 Traces |
| POST | /databases/all/migrate | migrate_all_databases | Database | target_version | — | inline / unspecified | OpenAPI security declared | F02/F16 or runtime utility |
| POST | /databases/{db_id}/migrate | migrate_database | Database | db_id, target_version | — | inline / unspecified | OpenAPI security declared | F02/F16 or runtime utility |
| GET | /components | disabled_components_get | Components | — | — | inline / unspecified | No operation security declared; runtime auth still verify | F16 System |
| PUT | /components | disabled_components_put | Components | — | — | inline / unspecified | No operation security declared; runtime auth still verify | F16 System |
| POST | /components | disabled_components_post | Components | — | — | inline / unspecified | No operation security declared; runtime auth still verify | F16 System |
| DELETE | /components | disabled_components_delete | Components | — | — | inline / unspecified | No operation security declared; runtime auth still verify | F16 System |
| PATCH | /components | disabled_components_patch | Components | — | — | inline / unspecified | No operation security declared; runtime auth still verify | F16 System |
| GET | /schedules | disabled_schedules_get | Schedules | — | — | inline / unspecified | No operation security declared; runtime auth still verify | F15 Schedules |
| PUT | /schedules | disabled_schedules_put | Schedules | — | — | inline / unspecified | No operation security declared; runtime auth still verify | F15 Schedules |
| POST | /schedules | disabled_schedules_post | Schedules | — | — | inline / unspecified | No operation security declared; runtime auth still verify | F15 Schedules |
| DELETE | /schedules | disabled_schedules_delete | Schedules | — | — | inline / unspecified | No operation security declared; runtime auth still verify | F15 Schedules |
| PATCH | /schedules | disabled_schedules_patch | Schedules | — | — | inline / unspecified | No operation security declared; runtime auth still verify | F15 Schedules |
| GET | /approvals | disabled_approvals_get | Approvals | — | — | inline / unspecified | No operation security declared; runtime auth still verify | F14 Approvals |
| PUT | /approvals | disabled_approvals_put | Approvals | — | — | inline / unspecified | No operation security declared; runtime auth still verify | F14 Approvals |
| POST | /approvals | disabled_approvals_post | Approvals | — | — | inline / unspecified | No operation security declared; runtime auth still verify | F14 Approvals |
| DELETE | /approvals | disabled_approvals_delete | Approvals | — | — | inline / unspecified | No operation security declared; runtime auth still verify | F14 Approvals |
| PATCH | /approvals | disabled_approvals_patch | Approvals | — | — | inline / unspecified | No operation security declared; runtime auth still verify | F14 Approvals |
| GET | /service-accounts | disabled_service-accounts_get | Service Accounts | — | — | inline / unspecified | No operation security declared; runtime auth still verify | F16 System |
| PUT | /service-accounts | disabled_service-accounts_put | Service Accounts | — | — | inline / unspecified | No operation security declared; runtime auth still verify | F16 System |
| POST | /service-accounts | disabled_service-accounts_post | Service Accounts | — | — | inline / unspecified | No operation security declared; runtime auth still verify | F16 System |
| DELETE | /service-accounts | disabled_service-accounts_delete | Service Accounts | — | — | inline / unspecified | No operation security declared; runtime auth still verify | F16 System |
| PATCH | /service-accounts | disabled_service-accounts_patch | Service Accounts | — | — | inline / unspecified | No operation security declared; runtime auth still verify | F16 System |
| GET | /registry | list_registry | Registry | resource_type, name, page, limit | — | #/components/schemas/PaginatedResponse_RegistryContentResponse_ | OpenAPI security declared | F02/F16 or runtime utility |
| GET | /factory/revision | factory_revision_factory_revision_get |  | — | — | inline / unspecified | No operation security declared; runtime auth still verify | F02/F16 or runtime utility |
| GET | /factory/workflows/{workflow_id} | factory_workflow_factory_workflows__workflow_id__get |  | workflow_id | — | inline / unspecified | No operation security declared; runtime auth still verify | F05/F07/F08 Workflows |
| GET | /factory/agents/{agent_id} | factory_agent_definition_factory_agents__agent_id__get |  | agent_id | — | inline / unspecified | No operation security declared; runtime auth still verify | F03 Agents |
| GET | /factory/teams/{team_id} | factory_team_definition_factory_teams__team_id__get |  | team_id | — | inline / unspecified | No operation security declared; runtime auth still verify | F04 Teams |

## Historical verified endpoints and data states (Agno 2.9.0)

| Request | 結果 | 已確認事項 |
|---|---:|---|
| GET /factory/revision，無 Authorization | 401 | Factory extension 繼承 AgentOS Bearer 認證。 |
| GET /factory/revision，有效 Bearer | 200 | revision bdcc8db58b2161b3；26 agents、3 teams、2 workflows。 |
| GET /factory/agents/factory-01 | 200 | 白名單回傳 ID/name/group/summary/inputs/outputs/skills/instructions/revision/source。 |
| GET /factory/teams/governance-team | 200 | 白名單回傳成員摘要、instructions、revision/source。 |
| GET /factory/workflows/software-delivery | 200 | 包含 Factory 設計步驟與 revision。 |
| GET /factory/workflows/unknown-workflow | 404 | 未知 ID 明確回 404。 |
| GET /workflows | 200 | 原生 runtime 清單回 2 個 workflow。 |
| GET /workflows/software-delivery | 200 | 原生 runtime 詳情回傳 steps；Condition/Parallel 有巢狀分支，Agent/Team 有穩定 component ID。 |
| UI 無 Token 使用受保護的 Agent/Team/Workflow 清單 | 401 | UI 把未授權顯示為錯誤狀態，不當作成功空集合。瀏覽器證據見實作紀錄。 |

API 檢查輸出僅記狀態碼、revision/counts、回應欄位名稱和去識別 schema，不顯示 token 或 prompt 內容。Factory 詳情掃描未發現 /app/、Windows 絕對路徑或 OS_SECURITY_KEY 標記。

## 能力狀態解讀

- 路由存在：只代表 OpenAPI 有 operation；不表示資源已配置、有資料或使用者有權限。
- 已配置：需檢查 AgentOS runtime/DB/config；例如本次 /approvals、/schedules 的可用性尚未逐條請求。
- 允許讀取：需以目前使用者認證對明確唯讀 endpoint 實測。3.2.1 的無 Token route-family probes 與有 Token 的已抽查 GET 結果見本文件的 live crosswalk；未列出的 operation 不推定授權行為。
- 有資料：需看 HTTP 回應筆數或內容數。Live crosswalk 分別記錄有資料、成功空集合、未配置及 disabled 503；這些狀態只適用於明確測過的 endpoint，不能由路由或同一 tag 推論其他資源狀態。
- 不呼叫會啟動模型、建立 run、重算 metrics、執行 evaluations、改變 approvals/schedules 或匯入資料的 API。

## 3.2.1 live tag-family route/config/auth/data crosswalk (2026-11-22)

From the running `factory-agentos` container, a read-only `/openapi.json` inspection confirmed OpenAPI 3.1.0, 94 paths, 135 unique HTTP operations, 164 component schemas, and the `HTTPBearer` scheme. The generated [operation inventory](agentos-api-openapi-3.2.1.md) records each operation's method, path, operationId, tags, parameters, request/response schema references, and operation-level security declaration. Five operations have no tag and are the POC Factory extension. Five Traces operations repeat the `Traces` tag in the source document; the counts below count each operation once.

A separate bounded, unauthenticated GET-only probe from inside the container requested 22 paths and printed only status codes/path names. `/`, `/health`, and `/info` returned 200; the other 19 paths returned 401. For authenticated status/data, this table uses the targeted GET audit above and earlier recorded Agent UI/runtime checks. “Not probed” is deliberately distinct from “empty” or “unavailable.” No write, migration, model-run, evaluation-run, or metrics-refresh operation was sent.

An additional authenticated read-only sample checked `/sessions/filter-schema`, `/traces/filter-schema`, `/memory_topics`, and a one-row `/user_memory_stats` page. The filter-schema responses returned 200 with 9 session fields／3 logical operators and 13 trace fields／2 logical operators; memory topics returned 200 with an empty array, and user memory stats returned 200 with an empty `data` array plus `meta`. OpenAPI response refs are `FilterSchemaResponse` for both filter-schema routes, inline for `/memory_topics`, and `PaginatedResponse_UserStatsSchema_` for user memory stats. Only response shape and aggregate counts were recorded; no IDs, personal values, prompts, or payload contents were retained. No run, evaluation, refresh, mutation, migration, approval/schedule, or import operation was called.

| OpenAPI tag | Unique operations | Capability mapping | Live route/config/auth/data evidence |
|---|---:|---|---|
| Agents | 12 | F03 | No-token `GET /agents` returned 401. Authorized list and sampled detail returned 200; 26 Agents are configured. Read-only Agent session/run list, sampled run detail, and checkpoint list/snapshot GETs returned 200; session page 1／2 returned one row each and page 999 returned zero. Agent create/cancel/continue/resume/fork POST operations were not called. |
| Teams | 11 | F04 | No-token `GET /teams` returned 401. Authorized list and sampled detail returned 200; 3 Teams are configured. Read-only Team session/run list, preview/detail and checkpoint list/snapshot GETs returned 200 for sampled existing records. Team create/cancel/continue/resume/fork POST operations were not called. |
| Workflows | 8 | F05/F07/F08 | No-token `GET /workflows` returned 401. Authorized list/detail returned 200; 2 Workflows are configured and sampled detail has 6 steps. Existing Workflow session run list/detail/preview GETs returned 200. Workflow create/cancel/continue/resume POST operations were not called. |
| Sessions | 13 | F01/F02/F07 | No-token paged list returned 401. Authorized `GET /sessions?limit=1&page=1` returned 200 with 1 session; an exact supplemental page 1／2 probe returned one row each, while page 999 returned zero. `GET /sessions/filter-schema` returned 200 with 9 fields and 3 logical operators. `limit`/`page` and session-run cursor/date filters are in the operation inventory. No successful wholly empty real DB or every schema variant was exercised. |
| Memory | 9 | F10 | No-token `GET /memories` returned 401. Authorized selected-DB list returned 200 with 0 records; the route declares `limit`/`page`. Supplemental `GET /memory_topics` returned 200 with 0 topics, and `GET /user_memory_stats?page=1&limit=1` returned 200 with `data=[]` and `meta`. These are successful empty responses; the latter stats route's data is empty, not proof of an unconfigured endpoint. |
| Learnings | 7 | F10 | No-token `GET /learnings` returned 401. Authorized selected-DB list and users/stat reads returned 200 with empty lists; list routes declare `limit`/`page`. |
| Knowledge | 13 | F09 | No-token config read returned 401. With authorization but no `db_id`, config/content returned 503; with the selected DB, config/content returned 404, consistent with no Knowledge instance configured. Content/source list routes declare `limit`/`page`; no content or search result exists to verify. |
| Traces | 5 | F11 | No-token `GET /traces` returned 401. Authorized traces/stats returned 200 with empty lists; the trace list declares `page`/`limit`. Supplemental `GET /traces/filter-schema` returned 200 with 13 fields and 2 logical operators. A non-empty Trace detail and positive Run-to-Trace link remain unverified. |
| Metrics | 11 | F12 | No-token `GET /metrics` returned 401. Authorized legacy metrics returned 200 with 2 rows; both refresh-status reads returned 200. No refresh was triggered. |
| Evals | 5 | F13 | No-token paged eval list returned 401. Authorized `GET /eval-runs?limit=10&page=1` returned 200 with `total_count=0` and `total_pages=0`; no eval run was created. |
| Approvals | 5 | F14 | No-token list returned 401; authorized list returned 503 with a configuration-dependent detail. This is disabled/unavailable, not empty. |
| Schedules | 5 | F15 | No-token list returned 401; authorized list returned 503 with a configuration-dependent detail. No schedule data is available. |
| Components | 5 | F16/F17 | No-token list returned 401; authorized list returned 503 with a configuration-dependent detail. No component records UI/data was verified. |
| Queue | 5 | F17 | No-token list returned 401; authorized list returned 503 with a configuration-dependent detail. Queue content is unavailable. |
| Service Accounts | 5 | F16/F17 | No-token list returned 401; authorized list returned 503 with a configuration-dependent detail. No account records are available. |
| Registry | 1 | F16/F17 | No-token paged list returned 401. Authorized pages returned 200; the live aggregate had 69 records over 35 API pages when queried with `limit=2`. The production UI uses 10 records/page and was browser-verified at 69 records over 7 pages: page 2 loaded different records; `resource_type=team` returned 3, name `Governance` returned 1, and Clear restored 69/7. `resource_type`, `name`, `page`, and `limit` are listed in OpenAPI. |
| Core | 2 | F16 | No-token `GET /config` returned 401; authorized config/info returned 200 with 1 available model. The v3 `/models` compatibility route returned 404. |
| Health | 1 | F16 | No-token `GET /health` returned 200 and `OK`. |
| Database | 2 | F17 | Both operations are POST migration routes. They are write operations and were not called; no read/config/data claim is inferred from route presence. |
| FileSystem | 4 | F17 runtime capability | Authorized GET sampling: `/filesystem/entries`, `/filesystem/files`, `/filesystem/search`, and `/filesystem/content` with `agent_id=factory-09` each returned 404, `This agent does not have a filesystem`. An unscoped `/filesystem/files?page=1&limit=1` returned 200 with `entries=[]`; this is not evidence of a configured filesystem or a configured-but-empty result. The response refs are `FileSystemListResponse`, `FileSystemTableResponse`, `FileSystemSearchResponse`, and `FileSystemContentResponse`, respectively. OpenAPI marks `query` required for search and `path` required for content; live handler behavior requires either `namespace` or `agent_id` for entries, search, and content (otherwise 400). No filesystem content was returned or recorded. |
| Media | 1 | F07 | OpenAPI declares `GET /sessions/{session_id}/media/{storage_key}` with required `session_id`/`storage_key` and 200 response content types `application/json` and `application/octet-stream` (no response schema ref). Authorized `GET /sessions?limit=5&page=1` returned 200 with 5 rows; the sampled metadata contained no media/storage references. A media GET using an existing session and an unavailable key returned 503, `Media storage is not configured on AgentOS`. No media bytes were downloaded. |
| Untagged (Factory extension) | 5 | F03/F04/F05/F16 | Includes `/factory/catalog`, `/factory/revision`, and Factory Agent/Team/Workflow definition reads. No-token catalog/revision returned 401; authorized catalog/revision and sampled detail reads returned 200. The extension is local to this POC, not an upstream Agno route. |

### Additional authenticated read-only runtime samples (2026-11-22)

This follow-up expands the runtime sample beyond the UI's initial queries. It was executed from the AgentOS container using authorization already configured in that container; the credential was used only in request headers and was not printed. Results below retain HTTP statuses, aggregate counts, and response-key shape only. No write, model/workflow execution, evaluation, refresh, import, or migration operation was sent.

| Read family | Additional live result | Limit |
|---|---|---|
| Agents / Teams / Workflows | List and sampled detail GETs returned 200; list counts were 26 / 3 / 2. Sampled details exposed the expected runtime component keys, Team `members`, and Workflow `steps`. | No exhaustive per-component field matrix or unknown-ID behavior for every family. |
| Sessions / runs | Agent, Team, and Workflow session list/detail reads returned 200. A component-scoped Agent session query returned 0 while the unfiltered page returned 1. Sampled Team session returned 5 runs and 5 run previews; a Team component run list returned 1. Sampled Workflow session returned 1 run and 1 preview. Corresponding sampled run detail GETs returned 200; the Team detail shape included messages, member responses, and tools, and the Workflow detail included 6 step results and 10 executor runs. | Counts describe only these existing records and do not prove all pages, DBs, or pagination boundaries. No new run was created. |
| Checkpoints / compactions | Agent and Team checkpoint list and snapshot reads returned 200 with one sampled checkpoint; compactions for Agent, Team, and Workflow sessions each returned 200 with an empty list. | Workflow checkpoint route is absent from OpenAPI. No non-empty compaction record was available. |
| Supporting reads | Both metrics refresh-status GETs returned 200; eval-run list returned 200 with 0 data rows and pagination metadata. Filter-schema, memory-topic, and user-memory stats results are described in the crosswalk above. | No refresh action or evaluation was triggered. |
| Unavailable detail/config | Knowledge config/content without `db_id` returned 503; unknown Knowledge-source, eval-run, Trace, Memory, and Learning detail reads returned 404. | These results do not establish the contents or behavior of configured Knowledge or known detail records. |

Remaining safe-read coverage includes query/DB/page edge combinations for the full GET surface, configured Knowledge source/file details, and non-empty Trace/Eval details. A route absent from OpenAPI is not treated as an implemented operation.

### F03/F04 Workflow reference matrix (2026-11-22)

An aggregate-only read compared the runtime Agent/Team lists with both Factory Workflow definitions. Both definitions loaded successfully; 13 of 26 Agents and all 3 Teams are referenced, and there were zero references whose IDs did not match a runtime component. Only counts were retained; component IDs, names, credentials, and definition bodies were not printed. This verifies the available reference matrix data, not every UI detail page or behavior when one definition fails.

### Safe pagination boundary sample (2026-11-22)

Authenticated GETs with `limit=1` sampled pages 1, 2, and 999 on the default database for Sessions, Memory, Learnings, Evals, Traces, and Registry. All requests returned HTTP 200. Sessions and Registry returned one row on pages 1 and 2 and zero rows on page 999 (47 and 69 total respectively); Memory, Learnings, Evals, and native Traces returned zero rows and zero total pages on all three requests. The command retained only status, top-level response keys, row counts, and pagination metadata; it did not print or persist records. This covers selected pagination edges only, not every GET's DB/query/page combinations.

### F07 session-run filter contract (2026-11-22)

An authorized read-only comparison against the existing Workflow session confirmed the 3.2.1 query contract for `GET /sessions/{session_id}/runs`: no filters and `status=COMPLETED` returned 200 with one run; `status=ERROR` returned 200 with zero runs; `status=FAILED` returned 400 and listed the accepted values `CANCELLED`, `COMPLETED`, `ERROR`, `PAUSED`, `PENDING`, `REGENERATED`, and `RUNNING`. `created_after` and `created_before` are Unix epoch seconds, not ISO strings: an ISO value returned 422 (`int_parsing`), while the equivalent second values returned 200 with the matching run. The UI now validates exact statuses before sending and serializes local date/time filters to UTC epoch seconds. This confirms only the tested Workflow session and does not establish that a failed run exists.

### 2026-11-23 session-run cursor audit

After the Docker restart, an authorized GET-only census queried the one configured DB's existing 47 sessions: 7 Agent, 11 Team, and 29 Workflow sessions. The runs-list GET returned 200 for all 47. `meta.total_count` showed three multi-run Agent sessions (at most three top-level runs); all Team and Workflow sessions had at most one top-level run. No session IDs, run IDs, or record bodies were retained.

For each of the three multi-run Agent sessions, full index sets were contiguous. With `limit=1`, `before_run_index=max` and `after_run_index=min` each returned the expected adjacent index with `has_more=true` (3/3 sessions passed both directions). Team responses require separate interpretation: their `data` arrays can include member child runs, so raw `data.length` is not the top-level pagination count. No Team execution was initiated.

This covers only records in the one configured DB at the time of the sample. Other query/DB/page combinations and future records remain open. Unauthorized reads returned 401; configured-but-disabled management families returned 503. A 404 is established only for Knowledge against the selected DB; it is not generalized to unknown IDs for every resource family. These distinctions must remain visible in UI acceptance records.

## Remaining v3 contract coverage

### Same-origin UI proxy check (2026-11-22)

- [x] The Next.js `/api/agentos/[...path]` route forwards the allowlisted GET／POST／DELETE calls to server-side `AGENTOS_URL`, preserving query parameters and POST bodies. The browser uses a same-origin URL for local AgentOS requests, which works in the ChatGPT in-app browser where direct localhost fetches reset the connection.
- [x] 2026-11-22 production checkpoint image `sha256:0a11f3d38a56df8924319a513a7c05f8395da99c123d901c3c28e55f3775465f`: `GET /api/agentos/health` returned 200; unauthenticated `GET /api/agentos/workflows` returned 401. No proxy Token environment variable was configured in that production container. This checkpoint was superseded first by image `sha256:335cab6…` and finally by `sha256:1d2e02e…` on 2026-11-23; earlier `813fe12…` and `d2eb8f…` images are also superseded.
- [ ] Authenticated operation sampling remains partial. The browser feature checks used a temporary development-only local auth fallback, removed before the final production build; this does not establish every proxied operation's request/response behavior.

### Bounded live GET sweep (2026-11-22)

- The live OpenAPI exposes 70 GET operations. A bounded authenticated sweep queried 62 routes with one-row limits where available; it skipped eight routes that can return file, content, or media bytes. It printed only route templates, statuses, response-key names, and aggregate counts. The local key was read inside the AgentOS container and was not printed or persisted by the command.
- The 62 probes returned 40 HTTP 200, 13 HTTP 404, 3 HTTP 422, and 6 HTTP 503. The script used schema-derived generic values and intentionally missing IDs for detail paths; those 404s do not establish that a family is disabled. Three 422s include generic path/cursor inputs, not a verified valid boundary. The 503s include configured-but-disabled management routes and the unconfigured users-metrics endpoint. No write, model run, evaluation, refresh, migration, or data import was called.
- Follow-up requests used existing session IDs without printing them: Agent session list page 1／2 returned one row each and page 999 returned zero; an existing Agent session's run list and component run list each returned one, run detail and checkpoint list returned 200. A sampled Team session returned one session but zero runs/previews. The existing Continuous Improvement workflow session returned one run preview; other session samples varied, so no type-wide run count is inferred. Memory, Learning, Eval, and Trace lists remained successful empty responses; Knowledge config for the selected DB returned 404.
- The sweep does not complete P0.3: query/DB/page boundaries are not exhaustive, eight file/content/media routes were skipped, generic 404／422 probes are inconclusive, and no configured Knowledge, positive Trace, non-empty Eval, FileSystem, or Media fixture exists. Existing targeted FileSystem／Media results remain in the crosswalk above.

- [x] OpenAPI inventory 與 tag-family mapping 已完成（94 paths／135 unique operations／164 schemas、21 standard tags 加上 5 untagged Factory extension operations）；詳細 operation、參數、schema refs、安全宣告及功能對照見上方 crosswalk。
- [x] 2026-11-22 已執行 bounded read-only survey：70 個 GET 抽查 62 個（40×200、13×404、3×422、6×503），並精確補查 Agent／Team／Workflow 的既有 run、preview、detail、checkpoint reads，Sessions page 1／2／999，filter-schema、memory topics、user stats，以及 FileSystem／Media 的安全唯讀端點。此子項只代表有界抽樣完成；參數邊界、8 個 byte/content routes、正向 Trace/Eval/Knowledge fixtures 與未抽樣 GET 仍開放，見下方 P0.3 限制。
- [x] 2026-11-23 restart follow-up: runs-list GET returned 200 for all 47 sessions in the one configured DB; all 3 multi-run Agent sessions passed contiguous-index and before／after cursor boundary checks with `limit=1`. No IDs or bodies were retained. This targeted F07 sample does not complete full operation/query/DB/page sampling; details and limits are in [session-run cursor audit](#2026-11-23-session-run-cursor-audit).
- [ ] Authenticated route/config/data runtime sampling 尚未逐 operation 完成。P0.3 仍缺其餘 read operations 及其 query／DB／pagination 邊界、configured Knowledge details、positive Trace/Eval data。寫入、migration、模型執行與 refresh 操作不屬於唯讀 contract audit。
- [x] 目前 UI 涉及的 DB-backed lists 已對照 OpenAPI pagination parameters，並記錄成功有資料、成功空集合、401、Knowledge 404/503、management 503；每種狀態僅套用至表內明確測過的 endpoint，不外推成所有 route 的通則。
- [x] F06 Tools／Skills／Models 的 live sources 已映射：Runtime tools 與 models 使用 `/config`（3.2.1 沒有 `/models`），Factory Skills／Agent reverse references 使用受認證的本機 `/factory/catalog` extension。
- [ ] F16 external integrations 的 API/UI mapping 已知 `/api/integrations/status` 探測 Gateway、Backstage、Langfuse health，但它不是 AgentOS OpenAPI route。Backstage Catalog Graph 已設定 `system:default/ai-factory` root，browser 可見 Catalog nodes／relations；隔離 Docker network 已驗三個 health probes 同時失敗時其他 AgentOS 卡片仍載入。Langfuse project/trace correlation 尚未驗證，故整合驗收仍未完成；詳見[驗收證據](agent-ui-verification-evidence.md#2026-11-22-f16-isolated-docker-network-outage-check)。
- [x] Historical 2026-11-22 ChatGPT in-app browser checks used a 375×844 viewport for System／Runs and image `0052fa…` System／Registry; those checks confirmed their layouts at that checkpoint only. The latest production image/browser result is recorded in [2026-11-23 restart and production image](agent-ui-verification-evidence.md#2026-11-23-final-ui-build-and-production-verification); new-image narrow viewport and 125% zoom remain unverified.

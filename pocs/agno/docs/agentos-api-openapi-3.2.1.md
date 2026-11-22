# Agno AgentOS 3.2.1 OpenAPI operation inventory

Generated from the running Docker AgentOS on 2026-11-22 (Taipei time). OpenAPI 3.1.0; 94 paths; 135 HTTP operations. The live app includes the POC-local `/factory/catalog` extension in addition to the upstream Agno 3.2.1 routes. The request uses the local container Bearer key in memory and does not print or save it.

The table records path/query parameters and schema references only. It does not store request/response examples, credentials, prompts, or raw configuration. The OpenAPI security column records the document declaration; runtime authorization must still be verified separately.

| Method | Path | operationId | Tags | Parameters (`in:name`) | Request schema | Success response schema | OpenAPI security |
|---|---|---|---|---|---|---|---|
| GET | `/agents` | `get_agents` | Agents | none | none | inline | operation |
| GET | `/agents/{agent_id}` | `get_agent` | Agents | path:agent_id | none | #/components/schemas/AgentResponse | operation |
| GET | `/agents/{agent_id}/runs` | `list_agent_runs` | Agents | path:agent_id, query:session_id, query:status | none | inline | operation |
| POST | `/agents/{agent_id}/runs` | `create_agent_run` | Agents | path:agent_id | #/components/schemas/Body_create_agent_run | inline | operation |
| GET | `/agents/{agent_id}/runs/{run_id}` | `get_agent_run` | Agents | path:agent_id, path:run_id, query:session_id | none | inline | operation |
| POST | `/agents/{agent_id}/runs/{run_id}/cancel` | `cancel_agent_run` | Agents | path:agent_id, path:run_id, query:session_id | none | inline | operation |
| GET | `/agents/{agent_id}/runs/{run_id}/checkpoints` | `list_agent_run_checkpoints` | Agents | path:agent_id, path:run_id, query:session_id | none | inline | operation |
| GET | `/agents/{agent_id}/runs/{run_id}/checkpoints/{message_index}` | `get_agent_run_checkpoint_snapshot` | Agents | path:agent_id, path:run_id, path:message_index, query:session_id | none | inline | operation |
| POST | `/agents/{agent_id}/runs/{run_id}/continue` | `continue_agent_run` | Agents | path:agent_id, path:run_id | #/components/schemas/Body_continue_agent_run | inline | operation |
| POST | `/agents/{agent_id}/runs/{run_id}/resume` | `resume_agent_run_stream` | Agents | path:agent_id, path:run_id | #/components/schemas/Body_resume_agent_run_stream | inline | operation |
| POST | `/agents/{agent_id}/sessions/{session_id}/compact` | `compact_agent_session` | Agents | path:agent_id, path:session_id, query:user_id | none | inline | operation |
| POST | `/agents/{agent_id}/sessions/{session_id}/fork` | `fork_agent_session` | Agents | path:agent_id, path:session_id, query:user_id | none | inline | operation |
| DELETE | `/approvals` | `disabled_approvals_delete` | Approvals | none | none | inline | not declared |
| GET | `/approvals` | `disabled_approvals_get` | Approvals | none | none | inline | not declared |
| PATCH | `/approvals` | `disabled_approvals_patch` | Approvals | none | none | inline | not declared |
| POST | `/approvals` | `disabled_approvals_post` | Approvals | none | none | inline | not declared |
| PUT | `/approvals` | `disabled_approvals_put` | Approvals | none | none | inline | not declared |
| DELETE | `/components` | `disabled_components_delete` | Components | none | none | inline | not declared |
| GET | `/components` | `disabled_components_get` | Components | none | none | inline | not declared |
| PATCH | `/components` | `disabled_components_patch` | Components | none | none | inline | not declared |
| POST | `/components` | `disabled_components_post` | Components | none | none | inline | not declared |
| PUT | `/components` | `disabled_components_put` | Components | none | none | inline | not declared |
| GET | `/config` | `get_config` | Core | none | none | #/components/schemas/ConfigResponse | operation |
| POST | `/databases/all/migrate` | `migrate_all_databases` | Database | query:target_version | none | inline | operation |
| POST | `/databases/{db_id}/migrate` | `migrate_database` | Database | path:db_id, query:target_version | none | inline | operation |
| DELETE | `/eval-runs` | `delete_eval_runs` | Evals | query:db_id, query:table | #/components/schemas/DeleteEvalRunsRequest | no body | operation |
| GET | `/eval-runs` | `get_eval_runs` | Evals | query:agent_id, query:team_id, query:workflow_id, query:model_id, query:type, query:limit, query:page, query:sort_by, query:sort_order, query:db_id, query:table, query:eval_types | none | #/components/schemas/PaginatedResponse_EvalSchema_ | operation |
| POST | `/eval-runs` | `run_eval` | Evals | query:db_id, query:table | #/components/schemas/EvalRunInput | #/components/schemas/EvalSchema | operation |
| GET | `/eval-runs/{eval_run_id}` | `get_eval_run` | Evals | path:eval_run_id, query:db_id, query:table | none | #/components/schemas/EvalSchema | operation |
| PATCH | `/eval-runs/{eval_run_id}` | `update_eval_run` | Evals | path:eval_run_id, query:db_id, query:table | #/components/schemas/UpdateEvalRunRequest | #/components/schemas/EvalSchema | operation |
| GET | `/factory/agents/{agent_id}` | `factory_agent_definition_factory_agents__agent_id__get` |  | path:agent_id | none | inline | not declared |
| GET | `/factory/catalog` | `factory_catalog_factory_catalog_get` |  | none | none | inline | not declared |
| GET | `/factory/revision` | `factory_revision_factory_revision_get` |  | none | none | inline | not declared |
| GET | `/factory/teams/{team_id}` | `factory_team_definition_factory_teams__team_id__get` |  | path:team_id | none | inline | not declared |
| GET | `/factory/workflows/{workflow_id}` | `factory_workflow_factory_workflows__workflow_id__get` |  | path:workflow_id | none | inline | not declared |
| GET | `/filesystem/content` | `read_filesystem_content` | FileSystem | query:namespace, query:agent_id, query:path, query:user_id, query:offset, query:limit | none | #/components/schemas/FileSystemContentResponse | operation |
| GET | `/filesystem/entries` | `list_filesystem_entries` | FileSystem | query:namespace, query:agent_id, query:directory, query:sort_by, query:sort_order, query:page, query:limit | none | #/components/schemas/FileSystemListResponse | operation |
| GET | `/filesystem/files` | `list_filesystem_files` | FileSystem | query:agent_id, query:namespace, query:query, query:sort_by, query:sort_order, query:page, query:limit | none | #/components/schemas/FileSystemTableResponse | operation |
| GET | `/filesystem/search` | `search_filesystem` | FileSystem | query:namespace, query:agent_id, query:query, query:directory, query:user_id, query:page, query:limit | none | #/components/schemas/FileSystemSearchResponse | operation |
| GET | `/health` | `health_check` | Health | none | none | #/components/schemas/HealthResponse | not declared |
| GET | `/info` | `get_info` | Core | none | none | #/components/schemas/InfoResponse | not declared |
| GET | `/knowledge/config` | `get_knowledge_config` | Knowledge | query:db_id, query:knowledge_id | none | #/components/schemas/ConfigResponseSchema | operation |
| DELETE | `/knowledge/content` | `delete_all_content` | Knowledge | query:db_id, query:knowledge_id | none | inline | operation |
| GET | `/knowledge/content` | `get_content` | Knowledge | query:limit, query:page, query:sort_by, query:sort_order, query:db_id, query:knowledge_id, query:parent_id | none | #/components/schemas/PaginatedResponse_ContentResponseSchema_ | operation |
| POST | `/knowledge/content` | `upload_content` | Knowledge | query:db_id, query:knowledge_id | #/components/schemas/Body_upload_content | #/components/schemas/ContentResponseSchema | operation |
| DELETE | `/knowledge/content/{content_id}` | `delete_content_by_id` | Knowledge | path:content_id, query:db_id, query:knowledge_id | none | #/components/schemas/ContentResponseSchema | operation |
| GET | `/knowledge/content/{content_id}` | `get_content_by_id` | Knowledge | path:content_id, query:db_id, query:knowledge_id | none | #/components/schemas/ContentResponseSchema | operation |
| PATCH | `/knowledge/content/{content_id}` | `update_content` | Knowledge | path:content_id, query:db_id, query:knowledge_id | #/components/schemas/Body_update_content | #/components/schemas/ContentResponseSchema | operation |
| POST | `/knowledge/content/{content_id}/refresh` | `refresh_content` | Knowledge | path:content_id, query:db_id, query:knowledge_id | none | #/components/schemas/ContentResponseSchema | operation |
| GET | `/knowledge/content/{content_id}/status` | `get_content_status` | Knowledge | path:content_id, query:db_id, query:knowledge_id | none | #/components/schemas/ContentStatusResponse | operation |
| POST | `/knowledge/remote-content` | `upload_remote_content` | Knowledge | query:db_id, query:knowledge_id | #/components/schemas/Body_upload_remote_content | #/components/schemas/ContentResponseSchema | operation |
| POST | `/knowledge/search` | `search_knowledge` | Knowledge | none | #/components/schemas/VectorSearchRequestSchema | #/components/schemas/PaginatedResponse_VectorSearchResult_ | operation |
| GET | `/knowledge/{knowledge_id}/sources` | `list_content_sources` | Knowledge | path:knowledge_id, query:db_id | none | inline | operation |
| GET | `/knowledge/{knowledge_id}/sources/{source_id}/files` | `list_source_files` | Knowledge | path:knowledge_id, path:source_id, query:prefix, query:limit, query:page, query:delimiter, query:db_id | none | #/components/schemas/SourceFilesResponseSchema | operation |
| GET | `/learnings` | `list_learnings` | Learnings | query:learning_type, query:user_id, query:agent_id, query:team_id, query:session_id, query:namespace, query:entity_id, query:entity_type, query:limit, query:page, query:sort_by, query:sort_order, query:db_id, query:table | none | #/components/schemas/PaginatedResponse_LearningResponse_ | operation |
| POST | `/learnings` | `create_learning` | Learnings | query:db_id, query:table | #/components/schemas/LearningCreate | #/components/schemas/LearningResponse | operation |
| GET | `/learnings/users` | `list_learning_users` | Learnings | query:learning_type, query:user_id, query:limit, query:page, query:sort_by, query:sort_order, query:db_id, query:table | none | #/components/schemas/PaginatedResponse_LearningUserStats_ | operation |
| DELETE | `/learnings/users/{user_id}` | `delete_learning_user` | Learnings | path:user_id, query:learning_type, query:db_id, query:table | none | no body | operation |
| DELETE | `/learnings/{learning_id}` | `delete_learning` | Learnings | path:learning_id, query:db_id, query:table | none | no body | operation |
| GET | `/learnings/{learning_id}` | `get_learning` | Learnings | path:learning_id, query:db_id, query:table | none | #/components/schemas/LearningResponse | operation |
| PATCH | `/learnings/{learning_id}` | `update_learning` | Learnings | path:learning_id, query:db_id, query:table | #/components/schemas/LearningUpdate | #/components/schemas/LearningResponse | operation |
| DELETE | `/memories` | `delete_memories` | Memory | query:db_id, query:table | #/components/schemas/DeleteMemoriesRequest | no body | operation |
| GET | `/memories` | `get_memories` | Memory | query:user_id, query:agent_id, query:team_id, query:search_content, query:limit, query:page, query:sort_by, query:sort_order, query:db_id, query:table, query:topics | none | #/components/schemas/PaginatedResponse_UserMemorySchema_ | operation |
| POST | `/memories` | `create_memory` | Memory | query:db_id, query:table | #/components/schemas/UserMemoryCreateSchema | #/components/schemas/UserMemorySchema | operation |
| DELETE | `/memories/{memory_id}` | `delete_memory` | Memory | path:memory_id, query:user_id, query:db_id, query:table | none | no body | operation |
| GET | `/memories/{memory_id}` | `get_memory` | Memory | path:memory_id, query:user_id, query:db_id, query:table | none | #/components/schemas/UserMemorySchema | operation |
| PATCH | `/memories/{memory_id}` | `update_memory` | Memory | path:memory_id, query:db_id, query:table | #/components/schemas/UserMemoryCreateSchema | #/components/schemas/UserMemorySchema | operation |
| GET | `/memory_topics` | `get_memory_topics` | Memory | query:user_id, query:db_id, query:table | none | inline | operation |
| GET | `/metrics` | `get_metrics` | Metrics | query:starting_date, query:ending_date, query:user_id, query:db_id, query:table | none | #/components/schemas/MetricsResponse | operation |
| POST | `/metrics/refresh` | `refresh_metrics` | Metrics | query:db_id, query:table, query:user_id, query:background, query:rebuild_from | none | inline | operation |
| GET | `/metrics/refresh/status` | `get_metrics_refresh_status` | Metrics | query:db_id, query:table | none | #/components/schemas/MetricsRefreshStatusResponse | operation |
| POST | `/optimize-memories` | `optimize_memories` | Memory | query:db_id, query:table | #/components/schemas/OptimizeMemoriesRequest | #/components/schemas/OptimizeMemoriesResponse | operation |
| GET | `/os/metrics/latency` | `get_os_latency_metrics` | Metrics | query:starting_date, query:ending_date, query:user_id, query:db_id, query:timeout_seconds | none | #/components/schemas/OSLatencyMetricsResponse | operation |
| GET | `/os/metrics/models` | `get_os_model_metrics` | Metrics | query:starting_date, query:ending_date, query:user_id, query:db_id, query:timeout_seconds | none | #/components/schemas/OSModelMetricsResponse | operation |
| POST | `/os/metrics/refresh` | `refresh_os_metrics` | Metrics | query:db_id, query:timeout_seconds | none | #/components/schemas/OSMetricsRefreshResponse | operation |
| GET | `/os/metrics/refresh/status` | `get_os_metrics_refresh_status` | Metrics | query:db_id, query:timeout_seconds | none | #/components/schemas/OSMetricsRefreshStatusResponse | operation |
| GET | `/os/metrics/runs` | `get_os_run_metrics` | Metrics | query:starting_date, query:ending_date, query:user_id, query:db_id, query:timeout_seconds | none | #/components/schemas/OSRunMetricsResponse | operation |
| GET | `/os/metrics/sessions` | `get_os_session_metrics` | Metrics | query:starting_date, query:ending_date, query:user_id, query:db_id, query:timeout_seconds | none | #/components/schemas/OSSessionMetricsResponse | operation |
| GET | `/os/metrics/tokens` | `get_os_token_metrics` | Metrics | query:starting_date, query:ending_date, query:user_id, query:db_id, query:timeout_seconds | none | #/components/schemas/OSTokenMetricsResponse | operation |
| GET | `/os/metrics/users` | `get_os_user_metrics` | Metrics | query:starting_date, query:ending_date | none | #/components/schemas/OSUserMetricsResponse | operation |
| DELETE | `/queue` | `disabled_queue_delete` | Queue | none | none | inline | not declared |
| GET | `/queue` | `disabled_queue_get` | Queue | none | none | inline | not declared |
| PATCH | `/queue` | `disabled_queue_patch` | Queue | none | none | inline | not declared |
| POST | `/queue` | `disabled_queue_post` | Queue | none | none | inline | not declared |
| PUT | `/queue` | `disabled_queue_put` | Queue | none | none | inline | not declared |
| GET | `/registry` | `list_registry` | Registry | query:resource_type, query:name, query:page, query:limit | none | #/components/schemas/PaginatedResponse_RegistryContentResponse_ | operation |
| DELETE | `/schedules` | `disabled_schedules_delete` | Schedules | none | none | inline | not declared |
| GET | `/schedules` | `disabled_schedules_get` | Schedules | none | none | inline | not declared |
| PATCH | `/schedules` | `disabled_schedules_patch` | Schedules | none | none | inline | not declared |
| POST | `/schedules` | `disabled_schedules_post` | Schedules | none | none | inline | not declared |
| PUT | `/schedules` | `disabled_schedules_put` | Schedules | none | none | inline | not declared |
| DELETE | `/service-accounts` | `disabled_service-accounts_delete` | Service Accounts | none | none | inline | not declared |
| GET | `/service-accounts` | `disabled_service-accounts_get` | Service Accounts | none | none | inline | not declared |
| PATCH | `/service-accounts` | `disabled_service-accounts_patch` | Service Accounts | none | none | inline | not declared |
| POST | `/service-accounts` | `disabled_service-accounts_post` | Service Accounts | none | none | inline | not declared |
| PUT | `/service-accounts` | `disabled_service-accounts_put` | Service Accounts | none | none | inline | not declared |
| DELETE | `/sessions` | `delete_sessions` | Sessions | query:user_id, query:db_id, query:table, query:delete_media | #/components/schemas/DeleteSessionRequest | no body | operation |
| GET | `/sessions` | `get_sessions` | Sessions | query:type, query:component_id, query:user_id, query:session_name, query:limit, query:page, query:sort_by, query:sort_order, query:db_id, query:table | none | #/components/schemas/PaginatedResponse_SessionSchema_ | operation |
| POST | `/sessions` | `create_session` | Sessions | query:type, query:db_id | #/components/schemas/CreateSessionRequest | inline | operation |
| GET | `/sessions/filter-schema` | `get_sessions_filter_schema` | Sessions | none | none | #/components/schemas/FilterSchemaResponse | operation |
| POST | `/sessions/search` | `search_sessions` | Sessions | query:db_id, query:table | #/components/schemas/SessionSearchRequest | #/components/schemas/PaginatedResponse_SessionSchema_ | operation |
| DELETE | `/sessions/{session_id}` | `delete_session` | Sessions | path:session_id, query:user_id, query:db_id, query:table, query:delete_media | none | no body | operation |
| GET | `/sessions/{session_id}` | `get_session_by_id` | Sessions | path:session_id, query:type, query:user_id, query:db_id, query:table | none | inline | operation |
| PATCH | `/sessions/{session_id}` | `update_session` | Sessions | path:session_id, query:type, query:user_id, query:db_id, query:table | #/components/schemas/UpdateSessionRequest | inline | operation |
| GET | `/sessions/{session_id}/compactions` | `get_session_compactions` | Sessions | path:session_id, query:type, query:user_id, query:db_id, query:table | none | inline | operation |
| GET | `/sessions/{session_id}/media/{storage_key}` | `get_session_media` | Media | path:session_id, path:storage_key, query:type, query:user_id, query:db_id, query:table, query:redirect | none | inline | operation |
| POST | `/sessions/{session_id}/rename` | `rename_session` | Sessions | path:session_id, query:type, query:user_id, query:db_id, query:table | #/components/schemas/Body_rename_session | inline | operation |
| GET | `/sessions/{session_id}/run-previews` | `get_session_run_previews` | Sessions | path:session_id, query:type, query:user_id, query:created_after, query:created_before, query:status, query:db_id, query:table | none | inline | operation |
| GET | `/sessions/{session_id}/runs` | `get_session_runs` | Sessions | path:session_id, query:type, query:user_id, query:created_after, query:created_before, query:status, query:limit, query:before_run_index, query:after_run_index, query:db_id, query:table | none | inline | operation |
| GET | `/sessions/{session_id}/runs/{run_id}` | `get_session_run` | Sessions | path:session_id, path:run_id, query:type, query:user_id, query:db_id, query:table | none | inline | operation |
| GET | `/teams` | `get_teams` | Teams | none | none | inline | operation |
| GET | `/teams/{team_id}` | `get_team` | Teams | path:team_id | none | #/components/schemas/TeamResponse | operation |
| GET | `/teams/{team_id}/runs` | `list_team_runs` | Teams | path:team_id, query:session_id, query:status | none | inline | operation |
| POST | `/teams/{team_id}/runs` | `create_team_run` | Teams | path:team_id | #/components/schemas/Body_create_team_run | inline | operation |
| GET | `/teams/{team_id}/runs/{run_id}` | `get_team_run` | Teams | path:team_id, path:run_id, query:session_id | none | inline | operation |
| POST | `/teams/{team_id}/runs/{run_id}/cancel` | `cancel_team_run` | Teams | path:team_id, path:run_id, query:session_id | none | inline | operation |
| GET | `/teams/{team_id}/runs/{run_id}/checkpoints` | `list_team_run_checkpoints` | Teams | path:team_id, path:run_id, query:session_id | none | inline | operation |
| GET | `/teams/{team_id}/runs/{run_id}/checkpoints/{message_index}` | `get_team_run_checkpoint_snapshot` | Teams | path:team_id, path:run_id, path:message_index, query:session_id | none | inline | operation |
| POST | `/teams/{team_id}/runs/{run_id}/continue` | `continue_team_run` | Teams | path:team_id, path:run_id | #/components/schemas/Body_continue_team_run | inline | operation |
| POST | `/teams/{team_id}/runs/{run_id}/resume` | `resume_team_run_stream` | Teams | path:team_id, path:run_id | #/components/schemas/Body_resume_team_run_stream | inline | operation |
| POST | `/teams/{team_id}/sessions/{session_id}/fork` | `fork_team_session` | Teams | path:team_id, path:session_id, query:user_id | none | inline | operation |
| GET | `/trace_session_stats` | `get_trace_stats` | Traces, Traces | query:user_id, query:agent_id, query:team_id, query:workflow_id, query:start_time, query:end_time, query:page, query:limit, query:db_id | none | #/components/schemas/PaginatedResponse_TraceSessionStats_ | operation |
| GET | `/traces` | `get_traces` | Traces, Traces | query:run_id, query:session_id, query:user_id, query:agent_id, query:team_id, query:workflow_id, query:status, query:start_time, query:end_time, query:page, query:limit, query:db_id | none | #/components/schemas/PaginatedResponse_TraceSummary_ | operation |
| GET | `/traces/filter-schema` | `get_traces_filter_schema` | Traces, Traces | none | none | #/components/schemas/FilterSchemaResponse | operation |
| POST | `/traces/search` | `search_traces` | Traces, Traces | query:db_id | #/components/schemas/TraceSearchRequest | inline | operation |
| GET | `/traces/{trace_id}` | `get_trace` | Traces, Traces | path:trace_id, query:span_id, query:run_id, query:db_id | none | inline | operation |
| GET | `/user_memory_stats` | `get_user_memory_stats` | Memory | query:limit, query:page, query:user_id, query:db_id, query:table | none | #/components/schemas/PaginatedResponse_UserStatsSchema_ | operation |
| GET | `/workflows` | `get_workflows` | Workflows | none | none | inline | operation |
| GET | `/workflows/{workflow_id}` | `get_workflow` | Workflows | path:workflow_id, query:version | none | #/components/schemas/WorkflowResponse | operation |
| GET | `/workflows/{workflow_id}/runs` | `list_workflow_runs` | Workflows | path:workflow_id, query:session_id, query:status, query:factory_input | none | inline | operation |
| POST | `/workflows/{workflow_id}/runs` | `create_workflow_run` | Workflows | path:workflow_id | #/components/schemas/Body_create_workflow_run | inline | operation |
| GET | `/workflows/{workflow_id}/runs/{run_id}` | `get_workflow_run` | Workflows | path:workflow_id, path:run_id, query:session_id, query:factory_input | none | inline | operation |
| POST | `/workflows/{workflow_id}/runs/{run_id}/cancel` | `cancel_workflow_run` | Workflows | path:workflow_id, path:run_id, query:session_id | none | inline | operation |
| POST | `/workflows/{workflow_id}/runs/{run_id}/continue` | `continue_workflow_run` | Workflows | path:workflow_id, path:run_id | #/components/schemas/Body_continue_workflow_run | inline | operation |
| POST | `/workflows/{workflow_id}/runs/{run_id}/resume` | `resume_workflow_run_stream` | Workflows | path:workflow_id, path:run_id | #/components/schemas/Body_resume_workflow_run_stream | inline | operation |

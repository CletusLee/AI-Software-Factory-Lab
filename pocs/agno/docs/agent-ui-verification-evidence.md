# Agno POC Agent UI 驗收與畫面證據

日期：2026-11-22（台灣時間）  
環境：`agno-factory-local` Docker Compose；Agent UI `http://127.0.0.1:3000`、AgentOS `http://localhost:7777`  
本節下方既有截圖多數是 Agno 2.9.0 時期所拍，不能當作 3.2.1 的新畫面證據。Agno 3.2.1 驗收另列於 [3.2.1 UI verification](#agno-321-ui-verification)。

本文件列出實際從 Docker UI 操作並截取的畫面。歷史 UI image `1a182c1...` 包含 Runs Explorer、只讀 Data Explorer、Observability Traces／Metrics，以及 read-only System & integrations。Data 頁可查 Memory、Learnings、Knowledge，並能區分成功但空資料、Knowledge 未配置及 content/search 端點不可用。Runs 頁支援 Agent／Team／Workflow、DB 篩選、URL 深連結還原、Sessions／Runs 與型別專屬詳情；summary 卡依可用寬度調整欄數。Observability 支援 trace/run/session/status 查詢、每日 metrics、DB/table/date filters，且可從 Workflow Run 精確跳至 Traces。System Explorer 顯示 AgentOS health/version、註冊元件、Factory revision、Session DB、模型與介面／MCP；未檢查的外部整合顯示 `Not checked`。這些圖片用來說明升級前已驗證的 UI checkpoint，不當作 Agno 3.2.1 畫面。使用者已明確授權可由我直接從本機 `.env` 複製 OS_SECURITY_KEY 到本機 Agent UI；Token 只在瀏覽器記憶體內使用、欄位遮罩，不輸出到聊天、文件或截圖。瀏覽器工具沒有錄影輸出能力，以截圖作為可重查證據。

## Agno 3.2.1 UI verification

### 2026-11-22 mobile inspector and metrics fixture

- ChatGPT in-app browser at 375×844 displayed a synthetic parallel Workflow Graph with three children. Their cards were each 272px wide, shared the same X coordinate and stacked vertically; viewport, document and body widths were 375px. A keyboard-only flow used Tab to focus a Graph step and Enter to open its dialog; the dialog initially focused Close, trapped Tab／Shift+Tab, and restored focus to the selected step after Escape. Close-button focus restoration was also checked.
- The isolated Metrics fixture omitted `total_tokens` from two daily rows: the UI showed `Incomplete` and `Not returned total` rather than a partial sum. A synthetic 2 runs／0% success response displayed 100% failure; Users 503 remained independent. This does not establish a real failed run.
- AgentOS 3.2.1 source inspection confirmed inclusive calendar-date bounds. `/os/metrics/*` documents both endpoint dates as inclusive and permits a same-day window in `/usr/local/lib/python3.12/site-packages/agno/os/routers/metrics/metrics.py:75-76,107-123`; its default date is based on `datetime.now(timezone.utc).date()`. The PostgreSQL row-read branches used by `/metrics` compare `date >= starting_date` and `date <= ending_date` in `agno/db/postgres/async_postgres.py:3561-3565` and `agno/db/postgres/postgres.py:4083-4088`. ChatGPT browser single-day requests with both dates set to `2026-11-17` returned one run for `/os/metrics/runs` and one daily row for `/metrics`; `2026-11-18` returned the previously observed successful zero-run result. This verifies inclusive date bounds, not every timezone edge case.
- Browser-only screenshots of the 375px parallel graph and keyboard-opened inspector were displayed in tool output; the supported browser interface did not export them to the repository. Docker CLI confirmed production image `sha256:0a11f3d38a56df8924319a513a7c05f8395da99c123d901c3c28e55f3775465f` is running; `/` and `/api/agentos/health` return 200 and unauthenticated workflows return 401. AgentOS 3.2.1 and the healthy database remain running. Both isolated fixture containers are not running (Docker reports `Exited (137)`).

### 2026-11-22 F16 isolated Docker network outage check

- Docker CLI started an AgentOS mock and bind-mounted Agent UI on a new isolated network (`codex-agentui-f16-20261122`), exposed only on loopback port 3003. `AGENTOS_URL` pointed to the mock; the isolated network did not contain `langfuse-web`, `agno-gateway`, or `backstage`, so the three integration hostnames could not resolve. No real token was used.
- ChatGPT in-app browser loaded `/?view=system`. AgentOS health, component counts, Factory revision, configured DBs, model/interface summaries and the Registry panel loaded from the mock. The External integrations panel reported `ERROR`; Langfuse, Gateway and Backstage each showed `UNREACHABLE` with their own check time.
- Clicking the panel Retry changed the three external check times and kept their unreachable states. The other loaded AgentOS panels and Registry remained intact. This verifies failure isolation with an isolated network outage; no production container or real integration service was stopped or reconfigured.
- The success and failure views were captured using the ChatGPT in-app browser screenshot API and inspected in its tool output. The browser has no supported repository image export, and no whole-computer screenshot was taken. Docker CLI removed both temporary containers and the isolated network after verification; production services were left untouched.

### 2026-11-22 previous production image `d2eb8f…` (superseded by `0a11f3…`)

- Docker production build applied `pocs/agno/agent-ui.patch`, compiled Next.js, completed lint, TypeScript, and static generation. Final image `sha256:d2eb8f10620c4e405bd360d1c14f436f3725b6f5e166c989abdb8c0df6d21b43` runs in `factory-agent-ui` on port 3000. AgentOS remains 3.2.1 and Agno DB is healthy; neither was rebuilt or restarted.
- Docker CLI checks from inside the UI container returned `GET /` 200, `GET /api/agentos/health` 200, and no-Authorization `GET /api/agentos/workflows` 401. The image build lists both `/api/agentos/[...path]` and `/api/integrations/status` routes. An intermediate rebuilt image `sha256:94d1cf…` initially returned 404 for both AgentOS proxy paths because the new dynamic route file had not been included in the Git-generated patch; the file was added to the patch, the image rebuilt, and the final image above passed the 200／401 boundary.
- Final cleanup check stopped `factory-agent-ui-fixture` and `factory-agentos-mock`; both are exited. The production Agent UI remains running on the recorded digest, AgentOS remains running on 3.2.1, and Agno DB remains healthy.
- After reloading the final image with `NO TOKEN SET`, ChatGPT in-app browser showed public health and runtime info as loaded, Factory revision/config/sessions as independent 401／Retry states, zeroed protected component/session cards, and the Session database selector still visible as `AgentOS default`. This verified stale protected data does not remain on reload and the selector stays available while protected config is unauthorized.
- A separate read-only Langfuse audit observed 1 project and 14,763 traces (2026-11-22); in 10 sampled trace details, none contained a top-level `sessionId`, an `agno.run.id` observation attribute, or session attributes. AgentOS native trace and trace-session stats remain empty; datasets remain 0. OTel exporter health does not establish positive AgentOS run-to-trace correlation; no model run was created.
- Screenshot of this final Overview state was captured with the ChatGPT in-app browser screenshot API and displayed for review. The mock 403 state and Workflow Tree／Graph labels were also captured in that browser only. No whole-computer screenshot was taken. The browser tool still does not expose a supported repository-file export path.

### 2026-11-22 isolated Docker fixture browser checks

- Added reproducible `pocs/agno/mock-agentos-fixture.mjs` and `pocs/agno/docker-compose.ui-fixture.yml`. The mock is on the Compose network with no host port; the bind-mounted UI is loopback-only at `127.0.0.1:3002`, with `AGENTOS_URL` pointed at the mock. No real AgentOS data, token, or model call is used.
- Overview with the `default` fixture returned HTTP 200 and an empty session list; the browser displayed “No sessions were returned for this database.” The `fixture-db-403` selection returned 403 with the no-permission message, Retry, and a visible selector. `fixture-db-503-once` returned 503, then per-source Retry returned 200/empty. `fixture-db-drop-once` dropped the upstream connection; the same-origin proxy surfaced HTTP 502, and Retry returned 200/empty.
- Slow `fixture-db-slow-a` was selected, then quickly changed to `fixture-db-fast-b`. After the delayed A response had time to return, the UI still selected B and showed only `Fast B result`; the stale A result did not overwrite B. A loading snapshot also showed the database selector during the request.
- `/?view=workflows` loaded the fixture definition in both Tree and Graph views. The browser displayed `Unsupported step (loop)`, `Unsupported step (router)`, and `Unsupported step (custom_step)`. This verifies fallback labels, not unknown-step execution semantics.
- Browser screenshots of the 403 Overview and Workflow Tree／Graph were captured with the ChatGPT in-app browser screenshot API and reviewed in tool output. They are not saved under `docs/screenshots/` because the browser tool has no supported file export path.

### 2026-11-22 previous production image `813fe12…`

- Docker build completed patch check/apply, Next.js compile, lint, TypeScript, and static generation. The running `factory-agent-ui` uses `sha256:813fe12a15be03f9ad5e4ba6b35216412e2a1ad1fe95b6e227c84ffa7d5a94fc`, belongs to Compose project `agno-factory-local`, and publishes port `3000`. AgentOS remains 3.2.1; `factory-agno-db` is healthy.
- Final production proxy boundary checked through Docker CLI: `GET /` and `/api/agentos/health` returned HTTP 200; unauthenticated `GET /api/agentos/workflows` returned HTTP 401. Production container has no `AGENTOS_PROXY_AUTH_TOKEN`; the proxy uses server-side `AGENTOS_URL` and forwards the user-provided Authorization header when present.
- This image also contains the F05 fallback label `Unsupported step (<type>)` for unknown Workflow step types. The production build compiled it, but no `loop`／`router`／unknown-type Workflow fixture was available for a browser display check.

### 2026-11-22 ChatGPT browser feature checks through the same-origin proxy

- ChatGPT in-app browser loaded the bind-mounted UI and loaded AgentOS data through `/api/agentos`; direct browser requests to AgentOS loopback had previously failed with a connection reset. During this browser-only verification, a temporary development-only auth fallback used the local `.env` key because the browser tab's in-memory Token field was empty. The fallback and dev container were removed before the final production build; no credential value was written to files, tool output, screenshots, or the production image.
- F03: Testing Agent detail showed its role, input/output contract, 2 Skills, and 4 runtime tools. Workflow reference list showed Software Delivery.
- F04: Knowledge Team showed 4 members, runtime delegate tool, and Software Delivery reference. Selecting Research added the return-Team URL state; returning restored Knowledge Team and its details.
- F05: Tree/Graph toggle worked. Software Delivery graph showed Readiness `TRUE`／`FALSE` branches and two parallel groups of 3. Selecting Code Proposal showed Previous／Next and Infrastructure Proposal／Integration Proposal siblings with stable paths.
- F07: `FAILED` was rejected locally with supported statuses and did not become a URL filter. `ERROR` returned a successful empty result. Taipei local range `2026-11-15 16:00–16:10` serialized to UTC `2026-11-15T08:00:00Z–08:10:00Z` and returned one existing run. An invalid `runs_created_after=not-a-date` deep link was removed and explained in the UI. Existing Workflow run showed 6 step results and 10 executor runs; compactions returned a successful empty list.
- F16: System showed AgentOS 3.2.1, 26 Agents／3 Teams／2 Workflows, 1 session DB, 1 model, revision and 69 Registry records／7 pages. Langfuse／Gateway／Backstage health checks returned 200. Approvals／Schedules／Components／Queue／Service Accounts returned 503. Retrying Approvals updated only its own check time; this verifies retry scope, not an injected API outage.
- Knowledge Team, Workflow Graph, and System screenshots were captured through the ChatGPT in-app browser screenshot API and reviewed in its tool output. No whole-computer screenshot was taken. The browser tool has no supported export path to save these images under `docs/screenshots/`. A viewport override attempt did not change `innerWidth` (it remained 1280 or 1410), so these images are not 375px evidence.

### V01 page-to-route evidence index

The in-app browser does not expose a HAR/network panel. This index maps the UI sections and observed values to the same-deployment read-only AgentOS results recorded in the API contract; it is not a packet capture. Docker inspection confirmed that UI, AgentOS, and Agno DB use Compose project `agno-factory-local`.

| UI page / action | Read-only method and path → status | Checkable result or limit |
|---|---|---|
| Overview | `GET /health`, `/info`, `/config`, `/factory/revision`, `/sessions?limit=5` → 200; `GET /approvals`, `/queue` → 503 | Health OK; AgentOS 3.2.1; 26 Agents／3 Teams／2 Workflows; revision; 5 recent sessions. Approvals／Queue state is unavailable, not empty. |
| Chat | Agent／Team conversation stream is inherited from the fork and routed through the same-origin AgentOS proxy; no live POST or model run was invoked in this acceptance pass. | Runtime stream completion, TCP disconnect and request-log isolation remain unverified under P0.4; no test target was provided. |
| Agents | `GET /agents`, `/agents/factory-09`, `/factory/agents/factory-09` → 200 | 26 agents; Testing Agent detail included 2 Skills and 4 Runtime tools; Workflow reference showed Software Delivery. |
| Teams | `GET /teams`, selected Team detail and Factory definition → 200 | 3 teams; Knowledge Team showed 4 members and Software Delivery reference. Selecting Research and returning restored the Team selection. |
| Workflows | `GET /workflows`, `/factory/workflows/{workflow_id}` → 200 | 2 workflows; Software Delivery definition had 22 nodes, two true/false conditions, and two parallel groups of 3. Selected Code Proposal showed Previous／Next and parallel peers. |
| Tools／Skills／Models | `GET /config`, `/factory/catalog` → 200; `GET /models` → 404 | 29/29 runtime components, 108 tools, 14 Skills; `/models` is not available in this AgentOS version, so models come from `/config.available_models`. |
| Sessions／Runs | `GET /sessions`, `/sessions/{session_id}/runs`, run detail and previews → 200 | The rechecked Workflow session had 1 session／1 `COMPLETED` run, 6 step results and 10 executor runs; compactions returned 200／empty. Recheckable run ID: `5898977d-3a48-4af6-a0a8-12e618b78724`. `FAILED` is locally rejected; `ERROR` is a successful empty response. |
| Knowledge／Memory／Learnings | `GET /memories`, `/learnings` → 200／0 items; `GET /knowledge/config?db_id=…` → 404 | Successful empty Memory/Learnings; selected DB has no Knowledge instance. No real records exist to verify content fields, pagination or search references. |
| Traces／Metrics／Evaluations | `GET /traces`, `/trace_session_stats` → 200／empty; `GET /metrics` → 200; `GET /eval-runs` → 200／0 items; `GET /os/metrics/users` → 503 | Metrics data and date/status filters were read; cost is not returned. No native Trace, positive run mapping, or Eval run exists. No real trace/eval ID is available to cite. |
| Approvals／Schedules／Operations | `GET /approvals`, `/schedules`, `/components`, `/queue`, `/service-accounts` → 503 with authorization | These routes are disabled/unavailable in the current AgentOS configuration; no approval or schedule record/ID exists. Retry on Approvals changed only its own check time. |
| System／Registry／Integrations | `GET /info`, `/config`, `/registry`, `/api/integrations/status` → 200 | System showed 3.2.1, component/database/model summaries and revision; Registry showed 69 records／7 UI pages; Gateway／Backstage／Langfuse health returned 200. Backstage Graph was separately browser-verified with the configured root; health still does not prove Langfuse trace correlation. |

The read-only Workflow reference sweep on 2026-11-22 loaded both Factory definitions successfully and matched their Agent／Team refs against the runtime lists: 13 of 26 Agents and all 3 Teams are referenced; there were zero unmatched refs. Component detail UI was browser-checked on Testing Agent and Knowledge Team; the full matrix result does not imply that every detail page or partial-definition-failure state was individually opened.

The same authorized read-only pass sampled `limit=1`, pages 1／2／999 for Sessions, Memory, Learnings, Evals, native Traces, and Registry. All returned 200; Sessions had 47 total rows and Registry 69, while the other four returned successful empty lists. Pages 1／2 each returned one row for Sessions and Registry; page 999 returned none. Only aggregate metadata was retained, with no record body or ID.

No write or model-run operation was issued in this evidence pass. The non-empty Trace/Eval/approval cases have no real IDs because their corresponding data or enabled routes are absent; that limitation is tracked under F11/F13/F14 and V04b.

### 2026-11-22 previous production images `a22fbf8…` and `7fa925d…` (superseded by `813fe12…`)

- Docker Compose built image `sha256:a22fbf8ddd67a6a88a21f33d41642c779a05a7b91d88437d9c5d499a10ea4ef5`; build output confirms patch check/apply, Next.js compile, lint, TypeScript, and static generation all succeeded.
- Docker CLI confirms `factory-agent-ui` is running on port `3000` with this image ID. From inside the UI container, `GET /` returned HTTP 200 and `GET http://factory-agentos:7777/health` returned HTTP 200. `factory-agent-ui`, `factory-agentos`, and `factory-agno-db` all report Compose project `agno-factory-local`; AgentOS remains 3.2.1 and was not restarted.
- The build includes F03/F04 Factory Workflow references on Agent/Team detail and F05 Tree/Graph toggle, responsive condition/parallel graph, and clickable Previous/Next/parallel-step relationships. Before production build, ESLint and `tsc --noEmit` passed in disposable Docker containers for both changed components. Read-only API review found two Workflow definitions (Software Delivery: 22 nodes, two condition branches and two parallel groups; Continuous Improvement: six root steps) and confirmed Agent/Team references can be computed from Factory definitions.
- ChatGPT in-app browser reloaded `http://127.0.0.1:3000` and visibly rendered the production Runs page at its existing 375px viewport. The page showed `NO TOKEN SET`; protected session requests returned HTTP 401 and Retry. Reload clears this UI's in-memory Token. The screenshot was captured only with the ChatGPT browser screenshot API and reviewed in its tool output; it was not captured from the desktop and could not be exported into the repository with a supported API.
- The image includes the F07 filter correction and F16 per-source retry scopes. The subsequent bind-mounted browser checks above verified the feature behavior. Final production was separately checked for unauthenticated health／protected route behavior.

### 2026-11-22 previous production image `c2f78c7…` and ChatGPT browser recheck (superseded)

- Docker CLI reports `factory-agent-ui` running on port `3000`, configured as `agno-factory-local-agent-ui:latest`, with image ID `sha256:c2f78c7b237b203bbfcd5bbbd9c9dbb5651cc94b97d237c05a1a97483eb88ec2`. The container-local `GET /` returned HTTP 200. `factory-agent-ui`, `factory-agentos`, and `factory-agno-db` all have Compose project label `agno-factory-local` and are running. AgentOS remains Agno 3.2.1; it was not restarted.
- F03 browser search at 375px: `factory-09` leaves only Testing Agent; `MiniMax-M3.1-Flash` finds 26 Agents and, after switching the list to Teams, 3 Teams. `OpenAI` provider search also matches the model-bearing components. Switching Agents／Teams updates the search placeholder and list. The search is case-insensitive, trims surrounding whitespace, and checks name, ID, model name／ID／provider.
- F12: a one-day `2026-11-17` `/metrics` request returned 1 row with 1 Workflow run/session and an explicit token total of 0. `/os/metrics/runs` returned 1 run and `success_rate=100`; the UI showed 0% failure. For `2026-11-18`, `/metrics` returned no daily rows and run/session/token summary values were 0; `/os/metrics/runs` returned zero runs and the UI showed failure rate `N/A`. Cost fields are absent and are not estimated. True failed／0%-success samples, missing-field fixtures, and date-boundary semantics remain unverified.
- The Metrics page at 375px measured `window.innerWidth`, document `scrollWidth`, and body `scrollWidth` as 375px. The UI displayed the two dates as the API's date strings, without shifting them across time zones.
- On first Metrics load, the database options showed `Failed to fetch`; clicking Refresh loaded the database option. No HTTP status was visible and no network fault was injected, so this is recorded only as a transient fetch error followed by recovery.
- The current Overview shows 26 Agents／3 Teams／2 Workflows and 5 recent sessions. `/approvals` and `/queue` each return authorized HTTP 503 and are labeled unavailable rather than empty. Clicking Approvals Retry updated only its last-checked time; Queue remained unchanged. The OpenAPI operations have no list schema, so the UI does not infer a pending count.
- Current System view shows health OK, AgentOS 3.2.1, 26／3／2 components, 1 session DB, 1 model, and the Factory revision. Registry reports 69 records／7 pages. Langfuse, Gateway, and Backstage health checks each return HTTP 200; these checks do not establish project／trace correlation. Registry type/name filtering and F04 member-return were verified on image `0052fa…` and were not repeated on this image.
- Read-only Langfuse API checks returned 200 for projects (1 project), traces (14,176 total／142 pages), and datasets (0 datasets). The sampled trace metadata did not expose AgentOS run/session identifiers; the trace list does not prove this POC's AgentOS executions were exported. There is no A/B dataset run available to inspect.
- Overview, Metrics, System, and search screenshots were captured via the ChatGPT in-app browser screenshot API and inspected in its tool output. The API does not provide a supported path to save screenshot bytes into `docs/screenshots/`; no whole-computer screenshot was taken. Actual 125% browser zoom remains unverified.

### 2026-11-22 image 439 initial browser state (historical; authorized results are above)

At this initial checkpoint, Agent UI image `sha256:439a8735afa27ddd42051f57642d045056e17effe2399a95f43b1a964d657a45` was running beside AgentOS 3.2.1 (`sha256:833882bc1e024e1acbc6ad9ce953c5b4b1bb0239451ea85f28a1ab17f8b013f2`). The build bundle contained the new read-only Registry panel. The ChatGPT in-app browser showed the panel, type/name filters, pagination, metadata allowlist, and an independent 401/Retry state with no Token. Health remained 200 and the three external health checks remained 200. The authorized list/filter/page results were verified later in the current production recheck above.

#### 2026-11-22 follow-up: image `439a8735…` versus existing tab (historical)

Docker inspect confirms `factory-agent-ui` is running the same `439a8735…` image, with working directory `/ui`; Next.js 15.5.18 logs `Ready`. The compiled page chunk `/ui/.next/static/chunks/app/page-ccb7e23c4e692cdf.js` contains the Registry panel heading. `factory-agent-ui` (`439a8735…`), `factory-agentos` (`833882bc…`), and `factory-agno-db` (`b0108689…`) all have the Compose project label `agno-factory-local` and are running.

At that time, the existing ChatGPT browser tab at `/?view=system` retained an in-memory Token (shown masked) and displayed the AgentOS 3.2.1 status card, management-route status cards, and three external health checks. Its page tree contained only the `/registry` HTTP 200 status card; it had no Registry records heading, filters, or pagination. The tab was not reloaded in that follow-up. This was later resolved by the authorized image `0052fa…` production browser recheck recorded above.

The current screenshot is visible in CUA tool output, but no supported screenshot file export is available. A localhost transfer attempt from the CUA runtime returned `fetch failed`; the temporary receiver was stopped and no screenshot file was created. Do not use this existing-tab image or the historical 2.9.0 screenshot as proof of the current Registry panel.

### F04 Team member return navigation (2026-11-22 initial dev checkpoint; superseded)

`AgentExplorer` now preserves the originating Team ID in the allowlisted `factory_return_team` query when a member opens in Agent details. `ComponentDetails` renders a Back to Team button; returning restores the Team selection and clears the return query. Manual component/type selection clears stale return state. The change is synced to `pocs/agno/agent-ui.patch` so a later production build includes it.

At this initial checkpoint the change was compiled from the bind-mounted dev container (`/ui/src` → workspace `agent-ui-delivery/src`); Next.js 15.5.18 compiled `/` and `pnpm exec tsc --noEmit` returned exit 0. The browser click-through and production rebuild were not yet done then. Dev logs also contained Watchpack `ENOMEM` scan warnings; the dev service was stopped. The current production click-through is recorded in the section above.

An earlier authorized GET audit returned 69 Registry records with pagination metadata (`limit=2`, `page=1`, `total_pages=35`, `total_count=69`): 26 agents, 3 teams, 2 workflows, 27 tools, 9 functions, 1 model, and 1 db. No record names, IDs, or metadata values were saved. The new browser screenshot was captured and visually inspected in tool output; no supported screenshot file API wrote it to `docs/screenshots/`.

For iterative UI work, [docker-compose.ui-dev.yml](../docker-compose.ui-dev.yml) reuses the local UI image's installed dependencies and bind-mounts `agent-ui-delivery/src` into `/ui/src` for `next dev`. Docker inspect confirmed the source mount and Next 15.5.18 reached Ready. Port 3002 failed CORS because AgentOS only allows localhost port 3000; the dev service was moved to port 3000 without widening CORS. Direct AgentOS reads from the mounted dev page stayed at Loading in the in-app browser, so this is an established build-free edit loop but not yet a verified dev API path. The dev service was stopped and the existing production image restored without rebuilding.

### 2026-11-22 Native Evals UI and button contrast recheck (image 9d41 checkpoint)

At this checkpoint, Agent UI image `sha256:9d41d8585e5e3828a11217bd638589789df10529278eb06539001f8ceb20f245` was running beside AgentOS 3.2.1 (`sha256:833882bc1e024e1acbc6ad9ce953c5b4b1bb0239451ea85f28a1ab17f8b013f2`). Docker production build completed Next compilation, lint, TypeScript checks, and static generation. The later image `439a8735…` adds the Registry records panel; see the current checkpoint above.

The ChatGPT in-app browser showed the new Observability → Evaluations view with the user-entered Token masked and a selected database. Authenticated `GET /eval-runs?limit=10&page=1` returned HTTP 200 with zero rows and pagination metadata (`page=1`, `limit=10`, `total_pages=0`, `total_count=0`). The UI displayed a successful empty state, an empty detail prompt, and a Langfuse note that no verified dataset run is available; it did not start an evaluation. A visual review caught a low-contrast default Filter button. Evals, Traces, Metrics, and Knowledge submit buttons now use the outline variant; the rebuilt Evals Filter appears dark with readable text. The browser screenshot was captured and inspected in tool output, but no supported API wrote it to `docs/screenshots/`.

### 2026-11-22 continuation recheck (image `3e55f72…`; historical)

At this historical checkpoint, Docker inspect showed `factory-agent-ui` (`sha256:3e55f721286f3e9b0383d0447e43d323e92eab0a1c65a87e57d93900886f843c`) and `factory-agentos` (`sha256:833882bc1e024e1acbc6ad9ce953c5b4b1bb0239451ea85f28a1ab17f8b013f2`) running. From inside the UI container, `GET /api/integrations/status` returned HTTP 200 with Langfuse, Gateway, and Backstage all at HTTP 200; the response contained only service IDs, status codes, and timestamps. In ChatGPT's in-app browser, the user-entered Token remained masked on the older `336c9a8…` page, where the protected System data had loaded. Image `3e55f72…` was a separate no-Token tab, showing 401 for protected routes and 200 for the three health probes. That page was captured and reviewed in browser tool output; this browser tool has no supported file export to save the image under `docs/screenshots/`. The later images `0052fa…`, `c2f78c7…`, and `a22fbf8…` are historical; the current image `7fa925d…` is documented at the top of this section.

Image `3e55f721…` 是較早的 production checkpoint：Docker build／deploy／inspect 成功，AgentOS `/health` 為 HTTP 200，`/openapi.json` 有 94 paths／135 operations 和 `/factory/catalog`。主要授權資料驗收先在 image `8f126975…` 完成；`4f57e9…` 加入 Sidebar Escape／focus-return，`bab1260…` 加入 endpoint 切換隔離，`7809386…` 修正初始化請求，`3e55f72…` 加上外部健康探測與管理路由 status checks。Agno DB health 也已由 Docker runtime 複核。Image `0052fa…` 是前一個 image，最新 `c2f78c7…` 見本節最上方。

| 範圍 | 3.2.1 驗收結果 | 證據／限制 |
| --- | --- | --- |
| Previous Docker deployment (`c2f78c7…`, superseded) | 該 checkpoint 的 Agent UI container 為 `running`，image ID `sha256:c2f78c7b237b203bbfcd5bbbd9c9dbb5651cc94b97d237c05a1a97483eb88ec2`；AgentOS 為 `cletus/agno-agentos:3.2.1`、image ID `sha256:833882bc1e024e1acbc6ad9ce953c5b4b1bb0239451ea85f28a1ab17f8b013f2`。 | 當時 Docker CLI 確認三個 POC containers 同屬 `agno-factory-local` project；UI port 3000、container-local `GET /` 回 200。該 image browser 覆驗搜尋、Metrics、Overview、System；Registry filtering 在前一 image `0052fa…` 驗收。現行部署見本節上方 `7fa925d…` checkpoint。 |
| Native AgentOS Evaluations | Read-only `GET /eval-runs?limit=10&page=1` 回 200、0 rows；meta 為 page 1、limit 10、0 pages、0 total. ChatGPT browser UI 顯示成功空狀態，提供 eval type、component type／ID、model ID 篩選、分頁與 run detail 入口。 | Detail JSON 預設收合；沒有資料可驗非空列、score／reason 或 run detail。Langfuse traces 存在但 datasets API 回 0，故無 A/B dataset run／score／trace correlation 可驗；沒有啟動評估或模型。截圖僅在 browser tool output，未存 repo。 |
| Dark-theme submit action contrast | Filter buttons in Evals and Traces, Load metrics, and Search knowledge now explicitly use the outline variant. | Rebuilt image `9d41d8…` was loaded in ChatGPT in-app browser; the Evals Filter rendered with a dark background and readable label. The Auth Token remained masked. |
| Targeted 3.2.1 GET route audit | No Authorization：`/health` 回 200；`/config`、`/agents`、`/factory/revision`、`/factory/catalog`、`/approvals`、`/components`、`/queue`、`/schedules`、`/service-accounts` 各回 401。 | 帶 Authorization 的 GET 抽查與計數已列於[API 契約](agentos-api-contract.md#321-targeted-read-only-get-audit-2026-11-22)；沒有呼叫寫入或執行端點，亦未保存 credential／raw detail。 |
| Management routes configuration state | 帶 Authorization 的 `/approvals`、`/components`、`/queue`、`/schedules`、`/service-accounts` 各回 503，response 只記錄有 `detail` 欄位並分類為 configuration-dependent。 | 這些不是成功空列表；沒有可用管理 UI 或項目資料。 |
| Authenticated System UI (image `336c9a8…`; historical) | 使用者在 ChatGPT browser 直接輸入 Token 後，System 頁顯示 health OK、Agno 3.2.1、26 Agents／3 Teams／2 Workflows、Factory revision `bdcc8db58b2161b3`、1 session DB、1 model、0 interfaces。 | `/approvals`、`/schedules`、`/components`、`/queue`、`/service-accounts` 回 HTTP 503；`/registry` status 為 HTTP 200。Token 欄遮罩。截圖在 browser tool output；沒有存 repo 檔，亦未記錄 Token 值。 |
| System management route checks (image `3e55f72…`; historical) | System Explorer 對 `/approvals`、`/schedules`、`/components`、`/queue`、`/service-accounts`、`/registry` 做唯讀 status checks；ChatGPT browser 無 Token 時六項均 HTTP 401，並列 last-checked time。 | 點 Approvals 的 `Recheck` 後該列時間由 `12:59:02` 改為 `12:59:28`；其他五列的時間維持 `12:59:02`，HTTP 401 不變。這證明重查只更新單一路由。status route 不讀 record bodies。 |
| Registry records panel (previous image `0052fa…`) | Image `0052fa5430b7…` shows the read-only panel, type/name filters, pagination, metadata allowlist, and global scope (`/registry` has no `db_id`). | Authorized ChatGPT browser returned 69 records / 7 pages; page 2 differed; type `team` returned 3, name `Governance` returned 1, and Clear restored 69 / 7. |
| External health checks (image `3e55f72…`; historical) | Agent UI Compose network 對 Langfuse `GET /api/public/health`、Gateway `GET /health`、Backstage `GET /healthcheck` 執行獨立唯讀 GET；browser UI 三項均顯示 HTTP 200 及最後檢查時間。 | 同源 `GET /api/integrations/status` 只回 service ID、HTTP status 或通用錯誤、timestamp；不回傳探測服務的 response body。這只證明 Agent UI 容器到健康路由可達。Backstage Catalog API 未登入回 401；Catalog Graph 與 Langfuse project／trace correlation 未驗。 |
| Runtime/System Explorer (previous image `0052fa…`) | ChatGPT in-app browser 實際顯示 AgentOS health `OK`、Agno `3.2.1`、26 Agents、3 Teams、2 Workflows、1 session DB、1 available model、0 interfaces；Factory revision counts 與 AgentOS 相符。 | Image `0052fa5430b7…` 的授權 System 頁也顯示 Registry 69 筆與獨立 HTTP status cards；screen captures are visible in browser tool output, with no supported repo screenshot-file export. Historical `system-explorer-desktop.jpg` remains a 2.9.0 screenshot. |
| Token 安全顯示 | UI Token 欄保持遮罩；只記 API 狀態和摘要，不保存金鑰。 | 畫面截圖中只有遮罩值。 |
| Docker image IDs at the c2 checkpoint | AgentOS 使用 `cletus/agno-agentos:3.2.1`，image config ID `sha256:833882bc1e024e1acbc6ad9ce953c5b4b1bb0239451ea85f28a1ab17f8b013f2`；該 checkpoint 的 Agent UI image ID `sha256:c2f78c7b237b203bbfcd5bbbd9c9dbb5651cc94b97d237c05a1a97483eb88ec2`。 | 這是歷史部署狀態；現行 Agent UI image 為本節上方記錄的 `sha256:813fe12…`。 |
| Workflow／Factory counts | UI 顯示 26 Agents、3 Teams、2 Workflows；Factory registry revision `bdcc8db58b2161b3` 與 AgentOS counts 一致。 | 由使用者已在頁面輸入的 Token 載入；未輸出 Token。 |
| F03 Agent／Team model search (image `c2f78c7…`) | ChatGPT in-app browser 375px 搜尋 `factory-09` 後只剩 Testing Agent；model `MiniMax-M3.1-Flash` 命中 26 Agents 及切換清單後的 3 Teams；provider `OpenAI` 也可命中。切換 Agents／Teams 後 placeholder 與列表跟著變更。 | Query 不分大小寫、會 trim，檢查名稱、ID、model name／ID／provider。其他 Agent 詳情欄位和 Team／Workflow 關聯仍未全盤點。畫面留在 browser tool output，未能匯出 repo 圖檔。 |
| Overview／Workflow session deep link | 3.2.1 Docker UI 顯示 26 Agents、3 Teams、2 Workflows、健康 OK、Factory revision 與最近 sessions。從 Overview 開啟 Continuous Improvement Workflow session 後，Runs 選到同一 session 與 `COMPLETED` run，顯示 6 step results／10 executor runs。 | Image `8f1269…` 的 ChatGPT in-app browser 375×844 資料驗收中，Overview URL 保留具名 `overview_db`，Runs 顯示同一 session/run；document/body 寬 375px。前一 image `bab1260…` 重新在 375×844、300×675 切過九個工作區，因 Token 不持久化而顯示 401／未授權狀態；本次覆驗其窄版 layout，未重載上述資料數字。 |
| Overview URL／reload／Back | 具名 `overview_db` reload 後保留選取；由 Workflow Runs 回 Overview 時 query 移除舊 session／run/component/db/agent filters；Browser Back 還原原 session、run、DB 與 `COMPLETED` run detail。 | Token 不在 reload 後持久化；重新輸入後資料來源重新載入。Overview 桌面截圖於本輪 browser tool output 擷取，沒有另存 repo 檔案。 |
| Overview independent Retry／fault isolation | 無 Token 時 Factory revision、Recent sessions、Registered components 各自顯示 401／Retry；final reload 後 health 與 info 成功而受保護來源獨立 401。隔離 mock 另驗 403、503 Retry、socket drop→502 Retry、200 empty、loading 與 slow DB A→fast DB B race。 | Final production reload 顯示空的受保護卡片且 Session database selector 留在畫面。成功空狀態只以 mock 驗，不代表真實部署有空 sessions。錯誤 Retry 不清除其他來源。 |
| Runtime tool parameter schema | 最新 Docker UI image `sha256:8f126975d3f2ac3f600f30604607996f16c63c2e0edd5054eb835bdac570feff` 的 Tools 目錄搜尋 Testing 後列出 4 個 Runtime tools；四張卡片的 `Parameter schema` 均成功展開。`load_work_item_context` 顯示 object schema、4 properties 及 `required: work_id`。 | ChatGPT in-app browser 375×844 下主內容寬 323px；schema disclosure 可展開。Token 僅遮罩；畫面顯示在 browser tool output，尚無 repo screenshot file。 |
| F06 Tools／Skills／Models catalog | Tools 由 `/config` 的 29／29 runtime components 提供 108 tools，卡片含來源種類／ID、endpoint、tool identity 和 schema。Skills 顯示完整 Factory snapshot 的 14 skills、instructions 及所有反向 Agent references；`model-usage-cost` 找到 Optimization／factory-19 和 Cost Control／factory-27，點擊正確選取 Cost Control。Models 顯示 `/config.available_models` 的 1 個 MiniMax-M3.1-Flash／OpenAI，並列出 29 個 runtime references。 | Image `8f1269…` 的三個目錄都於 375×844 驗收；Tools／Skills／Models 主內容寬 323px，長 Skill 和 Agent reference 在欄內換行。前一 image `bab1260…` 在 375px／300px 對九個工作區覆驗，Tools／Skills／Models 無水平溢位。`/factory/catalog` 在 live OpenAPI 有 operation；無 Authorization 的 Docker request 回 401。3.2.1 `GET /models` 回 404，且可用 model response 沒有額外 public parameters，UI 明確呈現未提供。截圖顯示於 browser tool output，尚無 repo screenshot file。 |
| P1.1 independent detail failure / retry | 本機合成 AgentOS fixture：`GET /factory/agents/factory-404` 回 404、`GET /agents/factory-404` 回 200；Retry Factory 後計數 1→2，runtime 維持 1。`GET /factory/agents/runtime-404` 回 200、`GET /agents/runtime-404` 回 404；Retry runtime 後計數 1→2，Factory 維持 1。 | Browser 中各自顯示來源錯誤／Retry，另一來源的成功詳情保留。fixture 沒有 OS Token，所有資料為合成值；只驗 UI 行為，不等同正式 AgentOS 的資料／auth contract。 |
| Sidebar init deduplication | 切換至 synthetic endpoint 後，fixture counters 顯示 `/health=1`、`/teams=1`、`/agents=1`；無快速重複初始化。 | 這筆計數來自匿名 loopback fixture，非 AgentOS telemetry；UI 已恢復 `http://localhost:7777`，Token 為 `NO TOKEN SET`。 |
| AgentOS operational metrics | Image `8f1269…` 上唯讀 `GET /os/metrics/{latency,models,runs,sessions,tokens,users}` 實查：latency／runs／sessions／tokens 各回 8 筆日資料，models 回 1 筆；各成功資料端點的回應都含其彙總欄位。Users 回 503，detail 為 `User metrics not available: pass a user_directory to AgentOS to enable this feature.` | 日期區間與適用的 `db_id` 由 UI 傳入。Users 端點不接受 DB 篩選。Observability Metrics 六張卡逐來源顯示狀態與 Retry；沒有列個人 user data，也沒有估算 cost。前一 image `bab1260…` 保留同一 Metrics 程式碼；reload 後 NO TOKEN SET 的 401 亦實際顯示。 |
| FileSystem and Media read routes | Authenticated FileSystem GET sampling: unscoped `/filesystem/files?page=1&limit=1` returned 200 with empty entries; scoped calls for `agent_id=factory-09` to entries/files/search/content all returned 404, `This agent does not have a filesystem`. Missing namespace/agent_id returns 400 on the scoped-required operations. | The unscoped empty response is not proof of a configured empty filesystem. Existing session-list response shape did not expose a media key; Media GET with an existing session and an unavailable key returned 503, `Media storage is not configured on AgentOS`. No media was fetched. OpenAPI response refs and params are in [API contract](agentos-api-contract.md#321-live-tag-family-routeconfigauthdata-crosswalk-2026-11-22). |
| F12 failure-rate and empty-range behavior (image `c2f78c7…`) | `2026-11-17` 單日 `/metrics` 回 1 row、1 Workflow run/session、token total 為明確的 0；`/os/metrics/runs` 回 1 run、success rate 100%，UI 顯示 0% failure。`2026-11-18` `/metrics` 無 daily rows，summary counts/tokens 為 0；runs endpoint 回 0，UI failure rate 為 N/A。 | 375px 下 `innerWidth`、document/body `scrollWidth` 均 375px。當時尚無真正 failed／0%-success run、missing-field fixture 或日期 source check；後續的 missing-field／synthetic-failure fixture 與 inclusive date-boundary 證據見本文件開頭。真實 failed run 仍無可用樣本。初次 DB options 載入顯示 `Failed to fetch`；Refresh 後成功，沒有觀察到 HTTP status，未注入網路故障。 |
| External service health | 2026-11-22 本機 Langfuse web／worker 與相依服務 running；`GET http://127.0.0.1:3001/api/public/health` 回 `200 {"status":"OK","version":"3.227.1"}`。AgentOS 啟動日誌顯示 `Langfuse OTel tracing enabled`。 | 這只證明服務健康及 exporter 初始化。Langfuse UI 顯示 Sign in；project／credentials／實際 trace 配對未核對，沒有執行新模型 run。 |
| Backstage Catalog／Graph | 2026-11-22 Guest Catalog API 有 48 entities：45 Components（26 Agents、3 Teams、2 Workflows、14 Skills）、1 Group、1 System、1 Location；共 366 relations，沒有 unresolved targets。將 `page:catalog-graph` root 設為 `system:default/ai-factory` 後，ChatGPT browser 的 `/catalog-graph` 顯示 Agents、Teams、Skills、Software Delivery、Continuous Improvement 等 nodes 和 relations，HTTP 200。 | Graph 空白問題已修正；config 以唯讀方式掛載到 Backstage。Browser screenshot 已在 tool output 擷取與目視檢查，未另存 repo。這不驗證 Langfuse trace／run 關聯或外部服務 outage isolation。 |
| Gateway report entry | 本機 `agno-gateway` 已啟動；ChatGPT in-app browser `GET http://127.0.0.1:7778/health` 回 `{"status":"ok"}`，`GET /report` 回成功 HTML。報告 title 為 `PAY-482 · Workflow 執行報告`，內容日期 2026-11-14，宿主檔案 `swarm-output/native-report.html` 為 1,286,635 bytes。 | 只驗既有報告可讀，不重跑 workflow／model，也不宣稱報告是當日新生成或包含可驗的 live Langfuse trace。Gateway／Langfuse／Backstage 目前為本機 Compose service。 |
| Earlier Overview narrow checkpoint (image `8f1269…`) | Image `8f1269…` 在 ChatGPT in-app browser 375×844 顯示 26 Agents、3 Teams、2 Workflows、5 recent sessions、health OK、Agno 3.2.1 與 Factory revision；URL 保留具名 `overview_db`。 | 資料驗收時 `innerWidth=375`、document/body scroll width `375px`；`main.clientWidth/main.scrollWidth=334/334px`。前一 image `bab1260…` 在 375×844 和 300×675 對 Overview、Chat、Workflows、Agents、Runs、Tools、Data、Observability、System 九個工作區逐一覆驗：兩種尺寸 document/body 均與 viewport 等寬；主內容分別寬 323–334px、248–259px，無水平溢位。300×675 是縮放尺寸代理，不是實際 125% zoom。 |
| Image `7809386…` Overview narrow checkpoint | Image `sha256:7809386…` 的 Overview 在 ChatGPT in-app browser 以 375×844 及 300×675 CSS viewport 載入；`innerWidth`、document `scrollWidth`、body `scrollWidth` 分別為 375px／375px／375px 及 300px／300px／300px。Health 為 OK；Factory、sessions、components 顯示各自 401／Retry。 | 此 checkpoint 為無 Token 狀態，不代表 image `3e55f72…` 新增 System cards 的窄版覆驗。新 image 只於 1280×720 桌面畫面檢查。截圖未寫入 repo。 |
| Token handling | 使用者在 ChatGPT browser 的 Agent UI Auth Token 欄位輸入本機 key；System 顯示遮罩並成功載入設定，文件只記錄非敏感狀態與 counts。 | 沒有讀取、抄錄或輸出 key。image `3e55f72…` 的獨立分頁未設定 Token；之後 image `0052fa…` 驗 Registry 清單，本輪 image `c2f78c7…` 也在此 ChatGPT browser 授權覆驗 System 與其他頁，見本節最上方。Browser auto-review 對額外 loopback bridge 的拒絕仍記錄為安全限制，沒有再使用該 bridge。 |
| Compact sidebar keyboard and focus | 前一 image `bab1260…` 在 300×675 viewport 展開抽屜後按 Escape，側欄收合且焦點回到 `Expand sidebar`；點抽屜外背景與選取 Tools 也會收合並還焦點至同一按鈕。由 Collapse sidebar 按 Tab 至 Overview、再按五次 Tab 到 Tools、Enter 切頁成功。 | `document/body=300px`；九個工作區主內容沒有水平溢位。此 CSS viewport 是 375×844 螢幕 125% zoom 的尺寸代理，不能作為實際瀏覽器 zoom 驗收。完整跨頁 Tab 順序與關閉詳情焦點仍待驗。 |
| Endpoint switch isolation | 前一 image `bab1260…` 的 sidebar endpoint change 清除 runtime Token、Agent／Team／session／message／model cache 與 endpoint-bound URL query，並 abort active stream／初始化讀取。最新 image 在 ChatGPT in-app browser 對 synthetic Agent 發送 `POST /agents/abort-fixture-agent/runs`：未切換 endpoint 的控制組如預期顯示 `late-fixture-marker`；第二次在 `RunStarted` 送達後立即切換至另一 loopback endpoint，fixture 延遲 10 秒再嘗試送 late marker。 | 切換後立即回到空白新聊天；延遲窗口過後主畫面仍沒有 late marker。fixture 總計 2 次 POST／2 次 late write attempt／0 次捕捉到 disconnect。沒有 callback instrumentation，故只確認切換後畫面未顯示晚到資料，不能斷言 callback 未被呼叫、TCP 中止或真實 AgentOS／模型串流。已還原 `http://localhost:7777`，Token `NO TOKEN SET`；Health OK，Factory、sessions、components 分別顯示 401／Retry。 |
| Session compactions | 現有 Workflow session 的 `GET /sessions/{session_id}/compactions` 回 200 空 array；Runs detail 顯示成功 empty state。 | 無 compaction records，因此尚無實際 compaction detail 可展示；UI 不生成不存在的 summary／archived messages。 |
| Docker Hub image | 公開 repository `cletus/agno-agentos:3.2.1` 的匿名 metadata API 顯示 `is_private=false`；tag 及 linux/amd64 manifest 可讀。 | Manifest digest：`sha256:6a13d301661dcef023c1d7d0d5264cd369a68c1cca4cb362698ba6749e77df70`。 |
| Compose image source | 預設 Compose 設定使用 `cletus/agno-agentos:3.2.1`；`docker compose pull agentos`、重建 container 後 `factory-agentos` 顯示相同 image tag 且容器內 Agno 版本為 3.2.1。 | 本 POC 仍需 repository checkout，因 Compose 從 checkout 掛載 Factory definitions、workflow handlers、scenario fixtures 與 integration source。 |
| Per-view URL allowlist | Runs → Overview 清除舊 `session_type`、`component_id`、`session_id`、`run_id`、`db_id`、`agent` 等查詢，保留 `view=overview` 與所選 `overview_db`；Browser Back 還原先前 Workflow session／run。Runs → System 的 URL 為 `?view=system`，待 config/catalog 等來源 hydration 後仍保持乾淨。 | 以 ChatGPT in-app browser 實際切頁並觀察 canonical URL。這驗證 UI query state 清理，未涵蓋所有外部 deep link 錯誤情境。 |
| Image `7809386…` mobile detail checkpoint | image `sha256:7809386e…` 在 ChatGPT in-app browser 375×844 載入 Agents 深連結；Factory／runtime 雙 401 錯誤卡各自顯示 Retry，過期 ID 保留在詳情標題。375px 畫面與 300×675 畫面截圖已在工具輸出。 | 375px 目視確認錯誤卡垂直排列、無可見水平溢位；300px 僅記錄截圖，未取得新 image 的 document/body 寬度數值。上一版 image `bab1260…` 的九工作區 375/300 測量仍按原 checkpoint 記錄，不冒稱本輪重測。 |
| Narrow viewport | Image `8f1269…` 在 ChatGPT in-app browser 實設 `375×844`；document/body 寬 375px；Overview 主內容 client／scroll 寬 334px，Runs／Tools／Skills／Models 約 323px，Observability Metrics 約 263px。前一 image `bab1260…` 在 375×844 與 300×675 覆驗九個工作區，均無水平溢位。Image `c2f78c7…` 再於 375px 覆驗搜尋、Metrics、Overview、System；Metrics 寬度 375px 無溢位。 | System 無 Token 狀態在 `8f1269…` 驗過；前 image `0052fa…` 授權 System／Registry 也量得 375px。實際 125% browser zoom 與完整鍵盤流程仍未驗。 |
| Screenshot artifact | Earlier screenshots captured in the ChatGPT in-app browser include Overview, Runs, Tools／Testing schema, Skills, Models, Metrics, System, 401／Retry, endpoint switch, Agent detail, Registry and Workflow. | The browser screenshot API does not expose repository file export; no whole-computer screenshot was taken. The last three screenshots in this earlier batch were desktop-size because that batch's viewport override did not take effect. Later 375px Workflow evidence is recorded above. |

## Historical verification evidence (Agno 2.9.0 UI checkpoints)

以下內容記錄升級前的既有 UI 驗收結果與畫面；不代表 AgentOS 3.2.1 新 endpoint 或新版本的窄版驗收。

## 驗收結果

| 範圍 | 驗收結果 | 證據 |
| --- | --- | --- |
| Docker UI 實際載入 | `http://127.0.0.1:3000` 顯示 Docker 建置的 Agent UI；資料從同一 Compose project 的 AgentOS 載入。 | [Software Delivery UI](screenshots/workflow-software-delivery.jpg) |
| Workflow 設計 | Software Delivery 共有 22 steps、11 agents、1 team；revision `bdcc8db58b2161b3`。Condition True/False 分支、Parallel Verification 子群組及 Agent 節點都可讀。 | [Workflow overview](screenshots/workflow-software-delivery.jpg) · [Parallel branches](screenshots/workflow-parallel-verification.jpg) |
| 第二條 Workflow 路徑 | Continuous Improvement 的 Workflow 可選取 Observability Team，查看 Team 資訊與成員。 | [Continuous Improvement + Team](screenshots/workflow-continuous-improvement.jpg) |
| Agent 詳情 | Testing Agent 可讀角色、摘要、I/O、Skills、完整 instructions、模型供應商／名稱、整合與 runtime tools。 | [Agent definition](screenshots/agent-testing-details.jpg) · [Agent runtime](screenshots/agent-testing-runtime.jpg) |
| 原始完整設定 | Factory registry 與 AgentOS component detail 有各自的 JSON disclosure，能檢視排版卡片尚未涵蓋的原生欄位。 | [Full Factory definition](screenshots/agent-testing-full-factory.jpg) · [Full AgentOS response](screenshots/agent-testing-runtime-raw.jpg) |
| Team 詳情及成員導覽 | Observability Team 可讀 instructions、coordinate mode、模型、delegate tool、四名成員及 AgentOS runtime member IDs；點選成員可前往 Agent 詳情。 | [Team definition](screenshots/team-observability-details.jpg) · [Team runtime](screenshots/team-observability-runtime.jpg) · [Member Agent](screenshots/team-member-agent-details.jpg) |
| Team 原始完整設定 | Team 的 Factory definition 和 AgentOS runtime JSON 可分別展開。 | [Full Team Factory definition](screenshots/team-observability-full-factory.jpg) · [Full Team AgentOS response](screenshots/team-observability-runtime-raw.jpg) |
| Token 重載行為 | 重載後回到 `NO TOKEN SET`，確認 Token 沒有持久化；依使用者授權，從本機 `.env` 恢復後由 UI 重新載入資料。 | [NO TOKEN SET after reload](screenshots/no-token-after-reload.jpg) · [Workflow 401 without token](screenshots/no-token-workflow-401.jpg) |
| Chat Sessions 成功清單 | Token 有效時側欄載入 7 筆既有 Agent Sessions。 | [Sessions loaded before layout fix](screenshots/chat-sessions-375px-before-fix.jpg) |
| Chat Sessions 認證錯誤 | 清除 Token 後 UI 清楚顯示 `AgentOS returned 401 Unauthorized` 與 Retry。 | [401 and Retry at 375px](screenshots/sessions-401-retry-drawer-375px.jpg) |
| 行動版側欄 | 375px 展開側欄改為浮層抽屜，背景遮罩下 Workflow 主欄仍維持完整寬度；收合後回到圖示導覽。 | [Open overlay drawer](screenshots/workflow-sidebar-drawer-open-375px.jpg) |
| Chat 窄版修正 | 375px welcome 標題折行，輸入框仍在可見主畫面內。 | [Chat welcome after fix](screenshots/chat-welcome-375px-after-fix.jpg) |
| Workflow Runs list | 375px 下可選 Workflow、瀏覽 Software Delivery 的 13 筆 sessions，分頁為每頁 5 筆／共 3 頁，選取 session 後列出 Workflow runs。 | [Workflow Runs session list](screenshots/workflow-runs-list-software-delivery-375px.jpg) |
| Workflow run detail | 實際 run detail 顯示狀態、step result／executor／event 數、pause 狀態、Workflow step results；完整 output 與原始 run response 可展開。 | [Workflow run details and steps](screenshots/workflow-run-details-software-delivery-375px.jpg) |
| Agent Runs | `sdlc-ticket-agent` 取得 7 筆 Agent sessions；抽樣 run `COMPLETED`，detail 顯示 6 messages、2 tool calls、metrics 與 Agent run data disclosures。 | [Agent run detail](screenshots/agent-runs-375px-details.jpg) |
| Team Runs | Observability Team 取得 1 筆 session、5 筆 Team runs；抽樣 run `COMPLETED`，detail 顯示 messages、工具／events 的回應狀態及 Team run data disclosures。 | [Team run detail](screenshots/team-runs-375px-details.jpg) |
| 有資料／空資料區分 | Governance Team 的 sessions endpoint 成功回傳 0 筆，UI 顯示 `No team sessions found for this component.`，沒有錯誤或假 session。 | [Empty result at 375px](screenshots/team-runs-empty-200-375px.jpg) |
| Runs 401 | 清除 Token 後 Runs component query 顯示 `AgentOS returned 401 Unauthorized` 與 Retry；重新由本機 `.env` 恢復授權 key 後資料可讀。 | [Runs 401／Retry at 375px](screenshots/runs-401-375px.jpg) |
| 三類 selector／Workflow 回歸 | 新版 UI 375px 顯示 Session type、Workflow selector、13 筆 session；run detail 仍顯示 Workflow step results。 | [Workflow selector and sessions](screenshots/workflow-runs-list-three-types-375px.jpg) · [Workflow run detail](screenshots/workflow-runs-detail-three-types-375px.jpg) |
| Runs DB filter（375px／desktop） | Database selector 從 AgentOS `/config.session.dbs[].db_id` 與元件清單 `db_id` 列出可用範圍。選 `AgentOS default` 移除 URL `db_id` 且資料仍載入；選具名 DB 後 Agent 仍載入 7 筆 sessions。重載後 DB query 保留，重新授權後 Runs 依該 query 載入。 | [375px DB filter](screenshots/runs-database-filter-375px.png) · [Desktop DB filter and run details](screenshots/runs-database-filter-desktop.png) |
| Observability Metrics | 選定 DB、2026-11-15 至 2026-11-21、table `agno_metrics`；AgentOS 回 2 日資料、35 runs、31 sessions 及 989,821 API-reported tokens。UI 顯示日期、範圍及成本未提供。 | [Metrics with DB/table](screenshots/observability-metrics-table-filter-desktop.jpg) |
| Metrics table validation | 選 AgentOS default（未指定 `db_id`）後輸入自訂 table，UI 說明要先選具名 DB，不送無效 API request。具名 DB + table 時的值保存在 URL，重載後重新授權仍恢復。 | [Table requires selected DB](screenshots/observability-metrics-table-requires-db-desktop.jpg) |
| Invalid Metrics table | 具名 DB 下送出不存在的 `codex_missing_table_verification`，AgentOS 回 500；UI 顯示完整狀態訊息與 Retry。API 實際回 500，未預設為 404。 | [Unknown table error and Retry](screenshots/observability-metrics-unknown-table-error-desktop.jpg) |
| Observability mobile layout | Traces 與 Metrics 在 375px 下 document width 都等於 viewport，無整頁水平溢位；篩選／摘要改直向排列。 | [Metrics 375px](screenshots/observability-metrics-375px.jpg) · [Traces 375px](screenshots/observability-traces-empty-375px.jpg) |
| Run → Trace 導覽 | 從真實 Continuous Improvement Workflow run 點 `View traces for this run`，進入 Observability／Traces，精確傳遞所選 Run ID 與 DB。AgentOS `/traces` 和 `/trace_session_stats` 對該 DB 回成功空結果；未把 run steps／其他 HTTP spans 當成 Trace。 | [Workflow Run action](screenshots/workflow-run-traces-link.jpg) · [Trace page filtered by that Run ID](screenshots/observability-run-trace-filter-empty-desktop.jpg) |
| System & integrations | 最新 Docker image 實際載入 AgentOS health／info／config／models 與 Factory revision；顯示 26 Agents、3 Teams、2 Workflows、1 Session DB、0 interfaces、1 model、MCP disabled。Factory revision 獨立呈現。Desktop 已驗；375px／部分來源失敗尚待驗。 | [System Explorer Desktop](screenshots/system-explorer-desktop.jpg) |

### 桌機 Workflow 畫面

![Software Delivery Workflow 與主要分支](screenshots/workflow-software-delivery.jpg)

![Parallel Verification 的 Testing、Security、Reliability 與 false path](screenshots/workflow-parallel-verification.jpg)

### Agent／Team 完整資訊

![Testing Agent 的結構化設定](screenshots/agent-testing-details.jpg)

![AgentOS runtime tools 與未回傳的 Knowledge／Memory 狀態](screenshots/agent-testing-runtime.jpg)

![Observability Team 的設定及成員](screenshots/team-observability-details.jpg)

### 窄版排版

修正前在 470px 時主內容 `clientWidth=202`、`scrollWidth=260`；375px 時為 `107`／`260`，內容確實被固定側欄擠壓。修正後 Sidebar 在 639px 以下自動收合成 40px 圖示導覽列。下表以 DOM 的 `clientWidth`／`scrollWidth` 檢查 document 與主內容區，兩者在測試點均一致，沒有整頁或主內容水平溢位。

| CSS viewport | document 寬度 | 主內容 client／scroll 寬度 | 證據 |
| ---: | ---: | ---: | --- |
| 590px | 590／590px | 538／538px | [590px Workflow](screenshots/workflow-590px.jpg) |
| 470px | 470／470px | 418／418px | [470px Workflow](screenshots/workflow-470px.jpg) |
| 375px | 375／375px | 323／323px | [375px Workflow](screenshots/workflow-375px.jpg) · [Parallel cards at 375px](screenshots/workflow-375px-parallel.jpg) |
| 375px Agent／Team | 375／375px | 323／323px | [Agent list and detail](screenshots/agent-testing-details-375px.jpg) · [Team member details](screenshots/team-observability-details-375px.jpg) |

![375px Parallel Verification branch remains readable](screenshots/workflow-375px-parallel.jpg)

JSON、instructions 和 tool 詳細文字區可在元件內自行捲動；這些是預期的內容區捲動，不是頁面本身發生水平溢位。

Workflow、Agent／Team 的上述窄版證據通過。新版 Docker UI 再以 375px 驗了 Chat welcome、Workflow 分支與 Agent 詳情。手動展開側欄時使用 overlay drawer，不再把主欄擠窄；Chat 標題折行且輸入框保持在畫面內。以下圖由先前的 Docker UI image 實際擷取；本輪最新 Runs 截圖另於下方以 `a0d9069...` 標示：

![Chat welcome at 375px after responsive fix](screenshots/chat-welcome-375px-after-fix.jpg)

![Software Delivery summary at 375px](screenshots/workflow-software-delivery-375px-after-drawer-fix.jpg)

![Parallel Verification agents at 375px](screenshots/workflow-parallel-verification-375px-after-drawer-fix.jpg)

![Expanded sidebar drawer over Workflow at 375px](screenshots/workflow-sidebar-drawer-open-375px.jpg)

![Testing Agent details at 375px](screenshots/agent-testing-details-375px-after-drawer-fix.jpg)

![Testing Agent runtime tools and raw runtime JSON at 375px](screenshots/agent-testing-runtime-375px-after-drawer-fix.jpg)

### Workflow Sessions／Runs（375px）

![Software Delivery Workflow session list and pagination](screenshots/workflow-runs-list-software-delivery-375px.jpg)

![Workflow run status, step results and expandable output](screenshots/workflow-run-details-software-delivery-375px.jpg)

### Agent／Team Runs 與回應狀態（375px）

![Agent run messages and tool-call details](screenshots/agent-runs-375px-details.jpg)

![Team run data disclosures](screenshots/team-runs-375px-details.jpg)

![Successful empty Team-session result](screenshots/team-runs-empty-200-375px.jpg)

![Unauthorized Runs query with Retry](screenshots/runs-401-375px.jpg)

![Workflow selector and session list after adding all three session types](screenshots/workflow-runs-list-three-types-375px.jpg)

![Workflow run detail regression at 375px](screenshots/workflow-runs-detail-three-types-375px.jpg)

### Runs DB 篩選與桌面詳情

![375px Runs DB selector and session list](screenshots/runs-database-filter-375px.png)

![Desktop Runs DB selector and workflow run details](screenshots/runs-database-filter-desktop.png)

### Runs 深連結與排版驗收（Docker image `a0d9069...`）

375px 選取 Agent 後，頁面 URL 同時保留原 Chat 的 `agent` 與 `db_id`，並新增 `view=runs`、`session_type`、`component_id`、`runs_page`、`session_id`、`run_id`。點第 2 頁後重載、重新授權，仍回到第 2 頁所選 Session／Run。

![Agent sessions at 375px after reload](screenshots/runs-deep-link-agent-375px-after-fix.png)

![Restored second Runs page at 375px](screenshots/runs-deep-link-page-2-375px.png)

![Agent session and run detail at desktop width](screenshots/runs-deep-link-agent-desktop.png)

![Agent run data disclosures at 375px](screenshots/runs-agent-data-375px.png)

- 非存在的 `session_id` 留在 URL 並提示該 Session 不在目前 DB／頁面，清單仍可供改選。
- 非存在的 `run_id` 顯示 AgentOS `404 Not Found` 和 Retry；有效 Run 仍可再選。
- 1280px summary cards 採兩欄，`Not returned` 和 `Returned` 不再垂直折字。375px 同樣使用兩欄卡片與可展開 run data。

### Data Explorer checkpoint（Docker image `e05479e...`；目前最新 image 見 Observability 區段）

- Data view 在 sidebar 有清楚入口；375px 下 Memory、Learnings、Knowledge tabs 與 DB selector 可用，卡片不會造成頁面水平溢位。
- 選定 DB 的 `/memories` 與 `/learnings` 都成功回應但沒有 records，UI 呈現成功空狀態及明確文字；這與 HTTP error 分開呈現。Knowledge config 回 404 時，UI 顯示該 DB 未配置 Knowledge instance 並提供 Retry。
- Data URL 使用 `view=data`、`data_type`、`db_id`。重載並重新授權後，頁面仍還原 Data view、Knowledge 分頁及同一 DB。
- 尚未驗有紀錄的 Memory／Learning、Knowledge instance 已配置時的內容清單／搜尋，因此欄位完整性、分頁與來源呈現仍待有資料環境驗收。

![Memory successful empty state at 375px](screenshots/data-memory-empty-375px.png)

![Knowledge not configured at 375px](screenshots/data-knowledge-unconfigured-375px.png)

![Knowledge not configured at desktop width after reload](screenshots/data-knowledge-unconfigured-desktop.png)

### Knowledge Configuration／Content／Search follow-up（2026-11-21）

- [x] 已核對運行容器 image 為 `sha256:e05479e55c3f173d60f7913e1b79d44245daa7fddc0a74f95a256e5d02c4a446`；Agent UI 與 AgentOS 為 running、Agno DB 為 healthy。
- [x] 依使用者先前授權，將本機目前設定的 key 寫入瀏覽器遮罩欄位；第一次 Refresh 仍有 401，重新保存目前 `.env` 設定後 Database selector 正常出現，401 消失。文件及畫面不包含 key 值。
- [x] `GET /knowledge/config?db_id=...` 的 404 顯示「No Knowledge instance is configured for this database.」，同時保留 Configuration／Content／Search 三個分頁。
- [x] `GET /knowledge/content` 的 404 顯示「No Knowledge content endpoint is available for this database.」及 Retry；這是後端目前未提供該端點，不記為成功空內容。
- [x] 在 Search 輸入一般驗證字串並執行唯讀 `POST /knowledge/search`，顯示未配置 Knowledge 提示與 Retry。URL 仍只有 `knowledge_view=search` 等狀態，沒有 query 文字。
- [x] 瀏覽器 375px viewport 的 `window.innerWidth`／document `scrollWidth` 均為 375。Search 輸入、模式及筆數控制改為垂直排列，錯誤卡與 Retry 可讀，無水平溢位。最新 375px Memory、Learnings 仍各為 HTTP 200／0 筆且顯示成功空狀態。
- [ ] Knowledge instance／內容未配置於此 DB，故仍未驗已配置資料的分頁、來源 metadata、搜尋結果及引用連結；不可用合成文件冒充真實 AgentOS 資料。

![375px Search query and stacked controls](screenshots/data-knowledge-search-unconfigured-375px-viewport.jpg)

![375px Search configuration error and Retry](screenshots/data-knowledge-search-unconfigured-375px.jpg)

![Desktop Knowledge Search unconfigured state](screenshots/data-knowledge-search-unconfigured-desktop.jpg)

![Desktop Knowledge Content endpoint unavailable](screenshots/data-knowledge-content-unavailable-desktop.jpg)

![Desktop Knowledge configuration unavailable](screenshots/data-knowledge-config-unavailable-desktop.jpg)

![Latest Docker UI Memory empty state at 375px](screenshots/data-memory-empty-375px-latest.jpg)

![Latest Docker UI Learnings empty state at 375px](screenshots/data-learnings-empty-375px-latest.jpg)

### Historical System Explorer（Agno 2.9.0 UI image `1a182c1...`，歷史畫面）

- [x] Docker inspect 確認 `factory-agent-ui` 使用 `sha256:1a182c1...` 且 running；`factory-agentos` running，`factory-agno-db` healthy。
- [x] 重載 `http://127.0.0.1:3000` 後確認瀏覽器載入最新 System Explorer；依使用者既有授權重新填入本機 Token 後，`GET /health`、`GET /info`、`GET /config`、`GET /models`、`GET /factory/revision` 均成功。健康 OK，Agno 2.9.0，26 agents、3 teams、2 workflows、1 session DB、0 interfaces、1 model；Factory revision component count 與 AgentOS config 相同。
- [x] 目視檢查桌面版：deployment、registered components、Factory registry snapshot、session storage、models、interfaces 及 external integrations 分卡呈現；Factory revision 可在 `/config` 來源失敗時獨立顯示。Agents／Teams／Workflows 的詳細清單為可展開區塊。
- [x] 外部整合沒有健康檢查結果時顯示 `NOT CHECKED` 中性狀態，不顯示綠色 Loaded；外部 gateway／Backstage／report 健康仍待另驗。
- [x] 截圖已覆蓋本地 Token 欄位，但只顯示遮罩，沒有憑證或完整 config。[System Explorer Desktop](screenshots/system-explorer-desktop.jpg)
- [ ] 尚未在 375px viewport 驗收 System Explorer，也未注入單一 API 來源錯誤以確認成功卡片保留；外部 Gateway／Backstage／report／Langfuse 健康需另行整合驗收。F16 因此仍未整體完成。

![Docker Agent UI 的 System Explorer 桌面畫面](screenshots/system-explorer-desktop.jpg)

### Observability Explorer（前一個已驗 Docker image `25d2e4b...`）

- [x] Docker inspect 確認 `factory-agent-ui` 使用 `sha256:25d2e4b...` 且 running；AgentOS running、Agno DB healthy。
- [x] Metrics 頁選定 DB 與實際 PostgreSQL table `agno_metrics`，唯讀 `GET /metrics?db_id=…&table=agno_metrics&starting_date=2026-11-15&ending_date=2026-11-21` 回 200、2 日 rows；總覽 35 runs、31 sessions、989,821 tokens。API 不回成本欄位，因此 UI 說明不提供／不估算。
- [x] DB selector 切至 AgentOS default 時移除 `db_id`；如仍填 table，顯示 `Select a specific database before choosing a table.` 並避免送出不合法查詢。切回具名 DB 後 table 查詢有效，query 狀態可 reload 恢復。桌面證據：[Metrics 實際資料](screenshots/observability-metrics-table-filter-desktop.jpg)、[table 需要具名 DB](screenshots/observability-metrics-table-requires-db-desktop.jpg)。
- [x] 以具名 DB 輸入不存在的 table `codex_missing_table_verification`，UI 顯示 `AgentOS returned 500 Internal Server Error` 與 Retry。這是 AgentOS 對此錯誤 table 的實際結果；證據：[Unknown table error and Retry](screenshots/observability-metrics-unknown-table-error-desktop.jpg)。
- [x] 從真實 Workflow run detail 點擊 `View traces for this run`，確認導覽設定 `view=observability`、`observability_view=traces`、精確 `trace_run_id`，並保留 `db_id`。Trace filter 使用該 run ID；AgentOS 回成功但 0 traces，`/trace_session_stats` 也回 0 sessions with traces。畫面：[Run detail 與按鈕](screenshots/workflow-run-traces-link.jpg)、[Trace 精確 run filter／空結果](screenshots/observability-run-trace-filter-empty-desktop.jpg)。
- [x] 以 375px viewport 驗證 Metrics／Traces，`window.innerWidth` 與 document `scrollWidth` 都為 375；沒有水平溢位。現有畫面：[Metrics 375px](screenshots/observability-metrics-375px.jpg)、[Traces 375px](screenshots/observability-traces-empty-375px.jpg)。桌面完整資料：[Metrics desktop](screenshots/observability-metrics-table-filter-desktop.jpg)、[Trace empty desktop](screenshots/observability-traces-empty-desktop.jpg)。
- [ ] 此 Agno DB 沒有原生 Trace，因此不能驗有資料的 Trace detail、span hierarchy、input/output 和正向 Run-to-Trace 關聯。等待有真實 Trace 的 fixture 後再補；不以合成 span、Workflow steps 或 Langfuse HTTP spans 冒充。

## Docker 與建置證據

- 歷史 System／Registry checkpoint image `sha256:0052fa5430b7eed45fc2d78eb0e29f04f71c7cb76c57252fb28eb7927ade7967` 已 Docker build／部署；其 patch apply、Next compile、lint、TypeScript 與 static generation 通過，ChatGPT browser 曾讀取 26 Agents／3 Teams 及 Registry records／filters／pagination。其後 image `c2f78c7…` 的搜尋、Metrics、Overview、System 畫面記錄於本文件上方歷史 checkpoint；現行 image `813fe12…` 的 build/runtime 證據列於本節最上方。
- 歷史 image `0052fa…` 由 `docker compose -f pocs/agno/docker-compose.yml build --progress plain agent-ui` build，並由 `docker compose -f pocs/agno/docker-compose.yml up -d --no-deps agent-ui` 部署。當時 Docker image ID：`0052fa5430b7`。
- AgentOS 的已知 Factory 與元件資料 API 實測：缺 Token 為 401，已知 ID 為 200，未知 Workflow ID 為 404，版本 revision 一致；UI 在使用者授權本機 key 後讀到 26 Agents、3 Teams、2 Workflows。
- Docker build 內完成 lint/typecheck/build；未另外新增或執行程式測試。

### F07 Sessions／Runs（Agent、Team、Workflow 首輪唯讀切片已驗）

- [x] `getAllSessionsAPI` 會對 HTTP 401／404／其他非成功狀態及網路錯誤丟出錯誤，不再回傳空資料偽裝成功。
- [x] Chat 側欄 Sessions 面板的程式碼加入錯誤分支與 Retry 控制，production build 通過。
- [x] Chat Sessions 有效 Token 成功載入 7 筆紀錄；新 Runs Explorer 以 Workflow 篩選取得 Workflow sessions，顯示 total、page、每頁筆數、session、run list 與 detail。
- [x] 375px 實測清除 Token 後 Sessions 顯示 `AgentOS returned 401 Unauthorized` 與 `Retry`；畫面見 [401／Retry](screenshots/sessions-401-retry-drawer-375px.jpg)。
- [x] 依使用者明確授權從本機 `.env` 恢復 Token；UI 顯示遮罩，重新載入 Agent／Workflow／7 筆 Sessions。
- [x] 375px Docker UI 實際載入 Agent 7 sessions、Team Observability 1 session／5 runs、Software Delivery Workflow 13 sessions／每頁 5 筆共 3 頁；Workflow 切至第 2 頁後仍會重新讀取 runs。
- [x] Agent run detail 顯示 `COMPLETED`、6 messages、2 tool calls、metrics；Team run detail 顯示 `COMPLETED` 與 message/tool/event disclosures；Workflow run detail 顯示 `COMPLETED`、2 step results、0 executor runs、0 events、Not paused。
- [x] Governance Team 的 0 筆成功結果顯示空狀態；清除 Token 後 AgentOS 回 401，Runs UI 顯示 `AgentOS returned 401 Unauthorized` 和 Retry。依使用者授權由本機 `.env` 恢復 key，瀏覽器只顯示遮罩。
- [x] DB selector 顯示 `/config.session.dbs[].db_id` 及元件 `db_id`；選回 AgentOS default 移除 query 後仍有 Workflow session，選具名 DB 後 Agent 仍有 7 sessions。重載後 query 保留，重新授權後 Runs 仍依所選 DB 載入。375px、1280px 視覺證據已保存。
- [x] Desktop Runs 詳情版面與資料卡已驗，見 [Desktop DB filter and run details](screenshots/runs-database-filter-desktop.png)。
- [x] Runs 深連結：`view`、type、component、page、session、run 選取寫進 URL；Agent page 1／page 2 重載並重新授權後還原，原有 Chat `agent` 和 DB `db_id` 保留。
- [x] 過期 Session 顯示 not-found 提示並保留清單供改選；過期 Run 顯示 AgentOS `404 Not Found` 和 Retry。有效 Run 可再選取。
- [x] 1280px summary cards 改成兩欄且文字可讀；375px Runs summary 和 Agent Run data disclosures 可瀏覽，證據見本節上方截圖。
- [ ] 斷線復原、跨 component／DB 深連結反例，以及有真實 Trace 時的 Run-to-Trace 正向關聯仍待驗。Run detail 導向精確 Trace run filter 已完成，結果為成功空資料；見上方 Observability 證據。

## 已知缺口與下次接手

- [x] 注入 Factory detail 404 和 AgentOS runtime 404，驗證局部降級、錯誤文字與重試按鈕：2026-11-22 以本機合成 fixture 完成，Retry 只重送失敗來源；合成回應不代表真實 AgentOS 的授權／資料狀態。Overview／System 的逐來源 401 隔離已於本輪另驗，不能代替 detail 404 故障注入。
- [x] Synthetic state 已驗 endpoint 切換會清除記憶體 Token、元件／session／message／model 快取與 endpoint-bound URL query；沒有在 URL 放 Token。
- [ ] 真實 AgentOS／模型 stream abort、callback 隔離與 request-log／記錄中的 Token 洩漏仍待驗；synthetic fixture 的 0 次 disconnect 不能代替真實串流驗收。
- [ ] 驗證實際 125% 瀏覽器縮放，以及尚未覆蓋的 Workflow graph node/details 純鍵盤操作。
- [x] 2026-11-22 current browser 375px：Tab 可遍歷側欄九個工作區，Enter 切至 System 後焦點回到 Expand sidebar；Escape 關閉 drawer 並還原焦點。Runs 頁的 Session／Run／Step controls 可鍵盤聚焦；Enter 開啟與收合 Observability step detail 後焦點留在同一 disclosure。
- [x] Chat welcome／輸入區與 Sidebar 展開狀態在 375px viewport 已實測通過；125% 縮放與鍵盤 focus／Esc 尚未驗。
- [x] 已完成 OpenAPI 全量靜態 operation／schema／tag-family mapping（94 paths／135 operations／164 schemas），並將既有 UI 相關 GET 抽查結果寫入 [API contract](agentos-api-contract.md)。
- [ ] Authenticated runtime 的認證、DB、分頁與錯誤仍未逐 operation 抽查；FileSystem、Media、非空 Trace detail 和其餘未抽樣 GET 待驗。Sessions／Runs、Data Explorer、Observability 已有唯讀頁面；Knowledge／Memory／Learning／Trace detail 的有資料畫面仍待真實 fixture。

接手時先看[實作與驗證紀錄](agent-ui-implementation-log.md)最新狀態，再按[功能計畫 checklist](agent-ui-capability-plan.md)逐項處理。避免重新建置或重拍已列為通過的項目，除非來源程式、Docker image 或 registry revision 已變更。

#### V03 續驗 checkpoint（2026-11-21）

- Data Explorer 最新 Docker image `sha256:030c154bfabb79172395197cdad3e0398cde9b940600e5212d7f6495215ca3cc` 已建置、部署並在 375px／1280px 瀏覽器驗收；Runs 深連結與排版 checkpoint 為前一版 `a0d90694...`，更早的 `69d5abd...`、`1787b49...`、`3ee954...`、`ea5cdf...` 是更早 UI checkpoint。
- Software Delivery 22 steps、11 agents、1 team、Parallel Verification 分支與 Testing Agent 的 Factory／runtime 詳情都可讀；行動版側欄抽屜不壓縮主內容。
- Chat welcome 可折行；Sessions 401 Retry 與 token 恢復後 7 筆 Sessions 均已驗。最新圖連結列於窄版排版與 Sessions 區段。
- Workflow Runs 的 13 筆 Software Delivery sessions、3 頁分頁、run detail 和 2 個已完成 Workflow steps 均由新版 Docker UI 載入；375px list/detail 截圖列於 F07 區段。
- 新版 Runs 已驗 Agent、Team、Workflow、0 筆成功結果和無 Token 401／Retry；截圖列於 Agent／Team Runs 區段。畫面未保存 Token。
- 新增 DB selector，驗 AgentOS default／具名 DB、`db_id` reload 保留；Runs URL 含 view、type、component、page、session、run 並已驗證 reload 恢復。Mobile／desktop 證據見 F07 區段。
- 新增只讀 Data Explorer：Memory／Learnings 空成功狀態、Knowledge 未配置狀態與 reload 後 URL 還原已驗；已保存 375px／桌面截圖。實際有資料與已配置 Knowledge 尚未驗。
- 125% 縮放、鍵盤 focus／Esc 與焦點返回仍待驗，故 V03 維持未完成。

#### 2026-11-22 pre-Registry-authorization System audit (historical; superseded by current checkpoint)

- [x] 當時 ChatGPT in-app browser 的 System 頁顯示 AgentOS 3.2.1、26 Agents／3 Teams／2 Workflows、1 session DB、1 model，Token 保持遮罩。Approvals／Schedules／Components／Queue／Service Accounts 為 HTTP 503；Registry 當時 HTTP 200 但尚未顯示 records 清單。後續 image 0052 的授權 Registry 清單／篩選／分頁已在本節頂部覆驗。外部 Langfuse／Gateway／Backstage 均為 health-only HTTP 200。
- [x] 本次畫面已在 ChatGPT browser tool output 擷取；未寫入 repo，因目前截圖操作沒有可用的 repository file export。
- [x] 較早 Docker CLI named pipe permission denied 已在後續本機 Docker CLI 複核完成：`factory-agent-ui` running，image ID `sha256:0052fa5430b7eed45fc2d78eb0e29f04f71c7cb76c57252fb28eb7927ade7967`；AgentOS 3.2.1 未重啟。
- [x] 此較早 checkpoint 不改變當時 V03／V05／V06 狀態，也不把 status-only endpoint 或缺資料的畫面標為功能驗收通過；目前狀態以本節頂部 0052 checkpoint 為準。

#### 2026-11-22 earlier 375px System／Runs checkpoint (viewport was reset then; later set to 375px again)

- [x] 該次 ChatGPT in-app browser viewport override 設為 375×844；System 的部署／元件／storage／models／interfaces／management／external cards 與 Runs session/run detail 均以直向窄版排列，逐段視覺檢視未見水平溢出。該次驗收後曾 reset viewport；後續 image 0052 recheck 又設為 375×844，且使用者 Escape 停止後續操作，目前 override 尚未 reset。
- [x] Runs URL 指向現有 Continuous Improvement Workflow session `ffea1d9d-aad6-4030-b68c-cfb4192b429c`／run `5898977d-3a48-4af6-a0a8-12e618b78724`；回應為 1 session、1 COMPLETED run、6 step results、10 executor runs、0 events、Not paused；compactions 回成功空集合。
- Note：以上只證明該次瀏覽器服務頁；當時 Docker Engine CLI 權限錯誤使 UI image digest 無法核對。後續 Docker CLI 已確認 image ID `sha256:0052fa5430b7eed45fc2d78eb0e29f04f71c7cb76c57252fb28eb7927ade7967`；最新窄版結果見文件頂部。
- [x] 實際 zoom 快捷鍵嘗試（Ctrl+Shift+= 兩次）沒有可辨識的畫面尺寸變化，之後以 Ctrl+0 還原；目前 in-app browser 未提供可檢查的 zoom percentage，故實際 125% 仍不算通過。

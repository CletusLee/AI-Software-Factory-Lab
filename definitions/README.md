# Shared definitions

Agent directory names include a stable ID and role name, such as `agents/factory-04-coder/`. The `id` in `agent.json` identifies the agent across POCs and historical records. Prompts, teams, skills, and workflows are maintained here. Each POC uses its own adapter to load and deploy them.

Workflow handler `ref` values are cross-POC capability names rather than platform-specific APIs. `software-delivery` and `continuous-improvement` are shared flows. Each POC case supplies work item data, and its adapter maps the execution details. The PAY-482 work item and acceptance cases are in `scenarios/pay-482/` and `benchmark/`. See `workflows/README.md` for reference relationships and current Agno POC coverage.

`reference_relationships.json` records the reference design's lateral support, failure returns, and post-approval relationships. Each POC should use its own workflows and actual traces to describe the relationships it implements.

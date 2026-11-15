# Local agent catalog and chat

Run `docker compose up -d --build`, then open Backstage at http://localhost:7007 and LibreChat at http://localhost:3080. Create a local account on first use, select the Agno endpoint, and choose an agent or team. Backstage component links can also open the corresponding LibreChat conversation.

At startup, `catalog-export` reads the shared definitions or deployed snapshot and generates the catalog and LibreChat model list. After changing shared definitions, run `python integration/deploy.py deploy`. Backstage component links also provide access to the shared Software Delivery workflow and work item execution evidence. PAY-482 is one example input.

The local gateway maps a LibreChat conversation to an AgentOS session and includes its text conversation history in each request. It returns a completed response over SSE. Attachments and token-by-token streaming are not yet supported. Backstage uses guest access, and service entry points bind to localhost by default. Configure authentication, permissions, and HTTPS before external or multi-user deployment.

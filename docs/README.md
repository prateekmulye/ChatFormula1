# docs/

The documentation set, in reading order:

| Document | What it covers |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | The blueprint: service boundary, schema, token streaming design, OTP showcase inventory, hosting topology |
| [ROADMAP.md](ROADMAP.md) | The six build phases, repo-hygiene log, and risk table |
| [STREAMING_PROTOCOL.md](STREAMING_PROTOCOL.md) | The frozen agent↔gateway NDJSON contract, with captured streams |
| [GRAPHQL.md](GRAPHQL.md) | Schema tour: the `AgentEvent` union, subscriptions, complexity limits, runnable operations |
| [DEPLOYMENT.md](DEPLOYMENT.md) | The Fly + Render + Supabase + Pinecone + Vercel free-tier runbook |
| [DEMO.md](DEMO.md) | The 5-minute demo script, beat by beat |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Quality gates and scope rules for PRs |
| [SECRETS_MANAGEMENT.md](SECRETS_MANAGEMENT.md) | What secrets exist and where they live |
| [TAVILY_INTEGRATION.md](TAVILY_INTEGRATION.md) | Web-search client details and free-tier budget |

## Decision records ([adr/](adr/))

| ADR | Decision |
|---|---|
| [000](adr/000-single-node-invariants.md) | Single node by declaration — the invariants that break at machine #2 |
| [001](adr/001-two-services.md) | Elixir gateway + Python inference engine, nothing more |
| [002](adr/002-model-agnostic-providers.md) | One provider factory speaking the OpenAI wire protocol (Ollama first-class) |
| [003](adr/003-ndjson-over-sse.md) | NDJSON over chunked HTTP for the internal stream, not SSE |
| [004](adr/004-supabase-over-neon.md) | Supabase Postgres — Oban polling kills Neon's compute-hour meter |
| [005](adr/005-showcase-mode.md) | SHOWCASE mode: cached replay as honest, graceful degradation |
| [006](adr/006-handrolled-rate-limiter.md) | Hand-rolled ETS rate limiter, deliberately not Hammer |

Per-app docs: [agent](../agent/README.md) · [gateway](../gateway/README.md) · [web](../web/README.md) · [web/DESIGN.md](../web/DESIGN.md)

`images/` holds the README screenshots.

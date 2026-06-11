# web/ — the cockpit

React 18 + TypeScript + Vite + Apollo frontend for ChatFormula1: streaming
chat with a live pipeline-telemetry strip, citation chips that land before
the answer finishes, the lights-out cold-start sequence, and standings /
calendar / drivers pages from pure GraphQL.

The design system is **Telemetry Noir** — see [DESIGN.md](DESIGN.md). It is
the source of truth for tokens, components, animation, and the anti-slop
rules; the Tailwind `@theme` block in `src/app.css` mirrors its §2.6.

## Run against a local gateway

```sh
# 1. Postgres + gateway (from the repo root)
make db                       # docker compose postgres:16
cd gateway && mix ecto.setup && mix phx.server

# 2. Frontend
cd web && npm install && npm run dev   # → http://localhost:5173
```

The Python agent being down is a designed state: sending a message exercises
the warming/lights-out UI and the circuit-breaker error path honestly.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `VITE_GRAPHQL_HTTP_URL` | `http://localhost:4000/graphql` | Queries + mutations (HTTP) |
| `VITE_GRAPHQL_WS_URL` | `ws://localhost:4000/socket/websocket` | Subscriptions (`graphql-ws`) |

The wake-on-paint `GET /up` ping and the GraphiQL link are derived from the
HTTP URL's origin. The gateway must list the frontend origin in its
`:cors_origins` config (the Vite dev origins are pre-wired in `dev.exs`).

## Scripts

| Command | What |
|---|---|
| `npm run dev` | Vite dev server |
| `npm run build` | `tsc -b` + production build |
| `npm test` | vitest (stream reducer, TokenStream, StatusBadge, CitationChip) |
| `npm run lint` | eslint (flat config) |
| `npm run codegen` | regenerate typed hooks from `schema.graphql` + documents |

`schema.graphql` is generated from the gateway
(`make codegen-web` from the repo root); CI fails on codegen drift.

## Token streaming, in one paragraph

`sendMessage` returns `{userMessage, assistantMessageId}` immediately; the
chat subscribes to `agentStream(assistantMessageId)` and reduces the
`AgentEvent` union in `src/features/chat/stream-reducer.ts` — idempotent by
`TokenDelta.seq` (reconnects replay the gateway buffer, so duplicates are
expected), with gap detection that falls back to refetching the completed
message from Postgres. `NodeTransition` drives the telemetry strip,
`SourcesResolved` renders citation chips before the text completes, and
`MessageCompleted` finalizes the bubble with latency + live/cached badges.

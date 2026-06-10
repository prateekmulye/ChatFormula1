# gateway — Phoenix GraphQL Gateway

Elixir 1.18 / Phoenix 1.8 / Absinthe 1.7 API-only gateway.  It is the only
public backend: GraphQL queries + mutations, conversation persistence, per-viewer
rate limiting, and a synchronous proxy to the Python agent service.

## What is here

| Layer | Technology |
|---|---|
| HTTP | Bandit + Phoenix 1.8 (no HTML/assets) |
| GraphQL | Absinthe 1.7, custom middleware (auth → rate limit → error normalization) |
| Database | Postgres 16 via Ecto 3 (Ecto.Multi, Ecto.Enum, migrations) |
| Association batching | Dataloader 2.0 Ecto source — N+1 free |
| Rate limiting | Hand-rolled ETS dual-window token bucket (per-minute + per-hour) |
| Agent proxy | Req 0.5 async NDJSON streaming — per-conversation GenServer + Task |
| Viewer identity | Anonymous Phoenix.Token (UUID scoped, 30-day TTL) |
| Telemetry | Phoenix/Ecto/Absinthe instrumentation + LiveDashboard at `/dev/dashboard` |

## Quick start

```sh
# 1. Start Postgres (docker-compose or local)
make db           # from repo root — starts postgres:16 via docker-compose

# 2. Install deps, create DB, run migrations
make setup-gateway

# 3. Seed F1 data (optional — reads data/ from the repo root)
cd gateway && mix run priv/repo/seeds.exs

# 4. Start the server
make dev-gateway   # listens on localhost:4000
# GraphiQL explorer: http://localhost:4000/graphiql
```

## Running tests

```sh
make test-gateway
# or directly:
cd gateway && mix test
```

## Lint gates

```sh
make lint-gateway
# runs: mix format --check-formatted && mix credo --strict
```

## Environment variables

| Variable | Required | Default (dev) | Description |
|---|---|---|---|
| `DATABASE_URL` | prod only | — | Ecto URL (`ecto://user:pass@host/db`) |
| `SECRET_KEY_BASE` | prod only | — | Phoenix secret (64+ bytes, `mix phx.gen.secret`) |
| `AGENT_URL` | prod only | `http://localhost:8000` | Internal URL of the Python agent |
| `INTERNAL_API_TOKEN` | prod only | `dev-token-not-a-secret` | Shared bearer token for agent calls |
| `PHX_HOST` | prod only | `chatformula1.com` | Public hostname for URL generation |
| `PORT` | optional | `4000` | HTTP listen port |
| `PGUSER` | dev/test | `postgres` | Postgres username |
| `PGPASSWORD` | dev/test | `postgres` | Postgres password |
| `PGHOST` | dev/test | `localhost` | Postgres host |
| `POOL_SIZE` | prod only | `5` | Ecto connection pool size |

## Phase 3 streaming (graphql-ws)

`sendMessage` is now **async**: it persists the message pair and returns
`{userMessage, assistantMessageId}` in < 50 ms.  The client then opens a
GraphQL subscription over the `graphql-ws` sub-protocol to receive events.

### WebSocket connection

```
wss://chatformula1.com/socket/websocket
sub-protocol: graphql-ws
```

`connection_init` payload **must** carry the viewer token:

```json
{ "token": "<viewer_token>" }
```

### Subscribe to a stream

```graphql
subscription AgentStream($mid: ID!) {
  agentStream(messageId: $mid) {
    ... on TokenDelta    { messageId seq text }
    ... on NodeTransition { messageId node startedAt }
    ... on SourcesResolved { messageId sources { kind title url snippet score } }
    ... on MessageCompleted { messageId cached usage { promptTokens completionTokens } }
    ... on AgentError     { messageId code message retryable }
  }
}
```

### Reconnect / replay

Reconnecting subscribers receive buffered events (up to 32 KB per message)
from the `Conversation.Server` replay buffer.  Events carry a monotonically-
increasing `seq` field; deduplicate by seq in the Apollo `InMemoryCache` reducer.

### System health

```graphql
query { systemHealth { mode gateway agentService database breakerState } }
subscription { systemHealthChanged { mode breakerState } }
```

### Architecture notes

- Every conversation is scoped to a `viewer_id` derived from the signed Phoenix.Token.
  IDOR is structurally prevented: every `Conversations` query includes `WHERE viewer_id = $1`.
- Rate limiter is a `GenServer`-owned ETS table (`ChatF1.RateLimit.Bucket`): writes are
  serialized through the GenServer for atomic check-and-consume; reads are direct ETS
  lookups (`public` table) for zero-copy hot-path access.
- Per-conversation `Conversation.Server` GenServers live under `ChatF1.ConversationSupervisor`
  (DynamicSupervisor).  A crash in one conversation never affects others (`one_for_one`).
- Circuit breaker `ChatF1.Agents.Breaker` guards the Python agent.  After 3 consecutive
  failures it opens; a health probe after 30 s closes it or re-opens.
- Supervision tree: `one_for_one` with
  `Repo → PubSub → Finch → RateLimit.Server → Telemetry → Breaker → ConvPipelineSupervisor → Endpoint`.
  See `lib/chat_f1/application.ex` for the annotated tree.

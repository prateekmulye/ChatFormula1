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
| Agent proxy | Req 0.5 synchronous NDJSON aggregation |
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

## Architecture notes

- Every conversation is scoped to a `viewer_id` derived from the signed Phoenix.Token.
  IDOR is structurally prevented: every `Conversations` query includes `WHERE viewer_id = $1`.
- Rate limiter is a `GenServer`-owned ETS table (`ChatF1.RateLimit.Bucket`): writes are
  serialized through the GenServer for atomic check-and-consume; reads are direct ETS
  lookups (`public` table) for zero-copy hot-path access.
- `sendMessage` is synchronous in Phase 2: it blocks until the agent responds (30 s timeout),
  aggregates the NDJSON stream, and returns the completed assistant message in one response.
  Phase 3 upgrades this to async + Phoenix Channel streaming.
- Supervision tree: `one_for_one` with `Repo → PubSub → Finch → RateLimit.Server → Telemetry → Endpoint`.
  See `lib/chat_f1/application.ex` for the annotated tree.

# Deployment Runbook — Free-Tier Topology

This is the runbook the owner executes to put ChatFormula1 on the
internet. It deliberately makes no "already deployed" claims — each
section is a step to perform, in order. The topology and its rationale
live in [ARCHITECTURE.md](ARCHITECTURE.md) §7; the single-node
constraints in [ADR-000](adr/000-single-node-invariants.md).

| Component | Provider | Plan | Why |
|---|---|---|---|
| Gateway | Fly.io | shared-cpu-1x 256 MB, count pinned to 1 | Terminates WebSockets, holds GenServer state — cannot sleep |
| Agent | Render | Free web service (sleeps after 15 min) | Cold start is a designed state; always-on would burn the free hours |
| Postgres | Supabase | Free (500 MB) | No compute-hour meter — Oban polling killed the Neon option ([ADR-004](adr/004-supabase-over-neon.md)) |
| Vectors | Pinecone | Starter serverless, `f1-knowledge`, aws/us-east-1 | Only free region; index is rebuildable via `make reindex` |
| Frontend | Vercel | Hobby | Static Vite build, PR preview deploys |
| LLM | OpenAI | gpt-4o-mini | The only variable cost; capped three ways (see §8) |

Fixed cost: $0/month. Verify each provider's current free allowance
before deploying — free tiers drift (this bit Fly once already, see
ROADMAP risk #6).

## 0. Prerequisites

- Accounts: Fly.io, Render, Supabase, Pinecone, Vercel, OpenAI, Tavily,
  plus this repo on GitHub.
- CLIs: `flyctl`, `vercel` (optional — the dashboard works too).
- Generate the two shared secrets now and keep them in a password
  manager:

```bash
# Internal bearer token (set identically on gateway AND agent):
python3 -c "import secrets; print(secrets.token_hex(32))"

# Phoenix secret:
cd gateway && mix phx.gen.secret
```

## 1. Supabase (Postgres)

1. Create a project (free tier). Region: pick the one closest to your
   Fly region.
2. Record two connection strings from the dashboard:
   - **Direct connection** (IPv6) — for the gateway on Fly, which has
     IPv6. Use with `ECTO_IPV6=true`.
   - **Session-mode pooler** (Supavisor, port 5432) — for running
     migrations/seeds from your laptop, which may be IPv4-only. Do not
     use transaction mode (port 6543): Ecto holds sessions.
3. Nothing depends on LISTEN/NOTIFY through the pooler — Oban is
   configured with `Oban.Notifiers.PG` (single node).
4. Supabase pauses free projects after 7 days of inactivity; the Oban
   cron jobs (nightly sync et al.) keep it awake once the gateway is up.

## 2. Pinecone (vector index)

1. Create a Starter serverless index named `f1-knowledge` in
   `aws/us-east-1` (the free region), dimension **1536**
   (text-embedding-3-small), metric cosine — or skip this and let the
   ingestion CLI create it.
2. From your laptop, with real keys in `agent/.env`:

```bash
make reindex   # delete + recreate the index with the configured dimension
make ingest    # chunk, embed, and upsert data/ with deterministic SHA-256 IDs
```

The index is cattle, not a pet: Starter indexes have been deleted for
inactivity before, and `make reindex && make ingest` rebuilds everything
from `data/` in one sitting.

## 3. Agent → Render

1. New **Web Service** → connect the GitHub repo → Root Directory
   `agent` → Runtime **Docker** (uses `agent/Dockerfile`) → Instance
   type **Free**.
2. Environment variables:

| Variable | Value |
|---|---|
| `OPENAI_API_KEY` | your key |
| `PINECONE_API_KEY` | your key |
| `TAVILY_API_KEY` | your key |
| `INTERNAL_API_TOKEN` | the shared token from §0 |
| `ENVIRONMENT` | `production` |

   (Provider overrides — `LLM_PROVIDER`, `LLM_MODEL`,
   `EMBEDDING_DIMENSION`, … — only if you are not on the OpenAI
   defaults; see `agent/.env.example`.)
3. Do **not** configure a Render HTTP health check: every agent route,
   including `/internal/health`, requires the bearer token, and Render's
   checker cannot send headers. The Dockerfile's own `HEALTHCHECK`
   covers liveness.
4. Note the service URL (e.g. `https://chatf1-agent.onrender.com`) —
   it becomes the gateway's `AGENT_URL`.
5. Verify from your laptop:

```bash
curl -H "Authorization: Bearer $INTERNAL_API_TOKEN" \
  https://<agent-host>/internal/health
```

The first request after idle takes 30–60 s — that is the cold start the
whole warming UX is designed around, not a problem to fix.

## 4. Gateway → Fly

The repo intentionally does not carry release artifacts yet; generate
and commit them as part of this step.

1. Generate the release + Dockerfile, then the Fly app:

```bash
cd gateway
mix phx.gen.release --docker     # rel/, Dockerfile, lib/chat_f1/release.ex
fly launch --no-deploy           # creates the app + a starter fly.toml
```

2. Edit `fly.toml` before the first deploy — these settings are
   load-bearing (ADR-000):

```toml
[http_service]
  internal_port = 4000
  force_https = true
  auto_stop_machines = false      # the gateway must never sleep
  auto_start_machines = true
  min_machines_running = 1

[http_service.checks]
  [http_service.checks.health]
    method = "GET"
    path = "/healthz"
    interval = "30s"
    timeout = "5s"

[env]
  PHX_SERVER = "true"
  ECTO_IPV6 = "true"
  ERL_FLAGS = "+hmqd off_heap"    # BEAM tuning for 256 MB

[deploy]
  release_command = "/app/bin/migrate"
```

3. Pin the machine count — one machine, one region, forever (or until
   ADR-000 is explicitly revisited):

```bash
fly scale count 1
fly scale memory 256
```

4. Secrets:

```bash
fly secrets set \
  DATABASE_URL='ecto://postgres:...@db.<project>.supabase.co:5432/postgres' \
  SECRET_KEY_BASE='<from mix phx.gen.secret>' \
  AGENT_URL='https://<agent-host>' \
  INTERNAL_API_TOKEN='<shared token>' \
  PHX_HOST='<fly-app>.fly.dev' \
  CORS_ORIGINS='https://<vercel-app>.vercel.app'
```

   `CORS_ORIGINS` is a comma-separated list of browser origins allowed
   to call the GraphQL API. It also feeds `check_origin` for the
   WebSocket upgrade (`config/runtime.exs` appends the gateway's own
   host) — if subscriptions fail with a 403 on connect, this list is
   the first thing to check. `DAILY_LLM_BUDGET_USD` is optional
   (default `2.00`).

5. Deploy and seed:

```bash
fly deploy                        # release_command runs migrations

# Seeds read from the repo's data/ directory, so run them from your
# laptop against the Supabase pooler URL (one-off):
cd gateway
DATABASE_URL='ecto://postgres:...@<pooler-host>:5432/postgres' \
SECRET_KEY_BASE='<any valid value>' \
AGENT_URL='https://<agent-host>' \
INTERNAL_API_TOKEN='<shared token>' \
MIX_ENV=prod mix run priv/repo/seeds.exs
```

6. Verify:

```bash
curl https://<fly-app>.fly.dev/healthz
# {"status":"ok","agent":"ready"|"down","mode":"live"|...}
```

   Open `https://<fly-app>.fly.dev/graphiql` and run the standings query
   from [GRAPHQL.md](GRAPHQL.md).

7. Generate an admin API key for LiveDashboard/metrics/ingest (prints
   the raw key once; only the SHA-256 hash is stored). Mix tasks are not
   available inside a release, so run it from your laptop against the
   pooler URL, with the same env vars as the seeds step:

```bash
cd gateway
DATABASE_URL='ecto://...' SECRET_KEY_BASE='...' AGENT_URL='...' INTERNAL_API_TOKEN='...' \
MIX_ENV=prod mix chat_f1.gen_api_key --scope admin:dashboard --scope admin:ingest
```

## 5. Frontend → Vercel

1. Import the repo → Framework **Vite** → Root Directory `web`.
2. Environment variables (Production):

| Variable | Value |
|---|---|
| `VITE_GRAPHQL_HTTP_URL` | `https://<fly-app>.fly.dev/graphql` |
| `VITE_GRAPHQL_WS_URL` | `wss://<fly-app>.fly.dev/socket/websocket` |

3. Deploy. PR preview deploys are on by default — note that previews
   run on per-deploy origins, so GraphQL calls from previews will be
   CORS-blocked unless you add their origin to `CORS_ORIGINS`;
   previews are for UI review, production origin is the wired one.
4. Verify: load the site, open the network tab — the first paint fires
   `GET <gateway>/up` (wake-on-paint), which also pre-warms the agent.

## 6. DNS cutover — chatformula1.com

Do this only after §1–§5 verify clean on the provider-issued hostnames.

1. **Gateway hostname:** give the API a stable name first.

```bash
fly certs add api.chatformula1.com
# At your DNS provider: CNAME api → <fly-app>.fly.dev
fly certs show api.chatformula1.com   # wait until issued
```

2. **Update the gateway env** to match the new public names:

```bash
fly secrets set \
  PHX_HOST='api.chatformula1.com' \
  CORS_ORIGINS='https://chatformula1.com,https://www.chatformula1.com'
```

3. **Frontend domain:** in Vercel → project → Domains, add
   `chatformula1.com` and `www.chatformula1.com`; create the A/CNAME
   records exactly as the dashboard prescribes.
4. **Update the frontend env** (`VITE_GRAPHQL_HTTP_URL` →
   `https://api.chatformula1.com/graphql`, `VITE_GRAPHQL_WS_URL` →
   `wss://api.chatformula1.com/socket/websocket`) and redeploy.
5. Verify end to end on the apex domain: chat streams, the telemetry
   strip moves, citation chips land before the answer finishes, and the
   footer disclaimer is visible.

## 7. wake-cron.yml — add at deploy time

This workflow is not in the repo yet because it has nothing to ping
until the services exist. Once §4 is done, commit it as
`.github/workflows/wake-cron.yml` (replace the URL if you skipped the
DNS cutover):

```yaml
# Daily wake ping. /up warms gateway + agent; /healthz doubles as an
# uptime check — a failure opens a GitHub issue (a public health trail).
name: wake-cron

on:
  schedule:
    - cron: "0 13 * * *" # daily, before US business hours
  workflow_dispatch:

env:
  GATEWAY_URL: https://api.chatformula1.com

jobs:
  wake:
    runs-on: ubuntu-latest
    permissions:
      issues: write
    steps:
      - name: Wake gateway and agent
        run: curl -fsS --max-time 30 "$GATEWAY_URL/up"

      - name: Health check (503 when degraded fails the step)
        run: sleep 75 && curl -fsS --max-time 30 "$GATEWAY_URL/healthz"

      - name: Open an issue on failure
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            await github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: `wake-cron failed ${new Date().toISOString().slice(0, 10)}`,
              body: "Daily uptime check failed — see the workflow run logs.",
            });
```

The 75 s sleep gives the agent's cold start time to finish so a routine
Render wake is not reported as an outage.

## 8. Spend caps — do not skip

Three independent layers, all of which must be on before the URL goes
on a resume (ROADMAP risk #4):

1. `DAILY_LLM_BUDGET_USD` (gateway, default 2.00) — the Postgres ledger
   flips the service into SHOWCASE cached-replay mode when spent.
2. **OpenAI account-level hard spend cap** — set it in the OpenAI
   billing console; this is the backstop the application cannot
   override.
3. Tavily free tier (1000 searches/mo) — the nightly ingest uses ~30;
   the agent's own 60/min limiter bounds runtime use.

## 9. Post-deploy checklist

- [ ] `GET /healthz` returns `"status":"ok"`
- [ ] GraphiQL standings query returns seeded data
- [ ] `sendMessage` + `agentStream` subscription streams tokens in GraphiQL
- [ ] Frontend chat streams with the telemetry strip moving
- [ ] Suspend the Render agent → breaker opens, UI shows the warming/degraded state, `systemHealth.mode` flips
- [ ] `demoQuestions` chips replay instantly with the cached badge in SHOWCASE
- [ ] LiveDashboard reachable with the `x-api-key` header, 401 without
- [ ] wake-cron.yml committed and green on a manual `workflow_dispatch`
- [ ] OpenAI hard spend cap set

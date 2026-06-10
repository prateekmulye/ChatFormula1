# ChatFormula1 v2 — Migration Roadmap

Companion to [ARCHITECTURE.md](ARCHITECTURE.md). Six phases, each ending **demoable in 5 minutes** — that gate is the scope-creep enforcement mechanism.

---

## Migration Roadmap

Each phase ends **demoable in 5 minutes** — that gate is the scope-creep enforcement mechanism.

### Phase 1 — Slim the engine (Python only, monorepo skeleton)
**Deliverables:**
- Repo restructured to `gateway/` (placeholder) + `agent/` + `web/` (placeholder) + `data/` + `docs/`.
- Dead code deleted in full (see [Repo Hygiene Actions](ROADMAP.md#repo-hygiene-actions)), including **explicit removal of the secret-injecting `ci-cd.yml`** that passed real API keys into unit tests on public PRs — named as a security fix in the migration notes.
- `graph.py`: missing `import asyncio` fixed (the `both` route currently 500s the most common query path); generation LLM tagged `["generation"]`; ContextScore multi-factor ranking salvaged from `nodes.py` into `rank_context` with dynamic year; graph compiled once at startup; `state.py` trimmed to `AgentState` + `QueryAnalysis`.
- Stateless `POST /internal/chat` (NDJSON, `astream_events` v2, tag-filtered) + `/internal/health` + bearer auth replacing the public FastAPI surface; per-session MemorySaver dict deleted; history accepted in payload.
- TavilyClient migrated to `langchain-tavily`; fake `crawl_f1_source`/`map_f1_domain` deleted. `providers.py` factory seam with **gpt-4o-mini** default. Settings decomposed so tests run without API keys (import-time `Settings()` broken).
- Exact version pins for langgraph/langchain; NDJSON **contract test** asserting the exact event sequence.
- Fresh path-filtered `agent.yml` CI, **green** (ruff + mypy + pytest, dummy keys only); stale `F1-Slipstream` assertions fixed.

**Demoable:** `curl -N` streams clean typed NDJSON for "who won the last race" — no analysis-JSON leakage; recorded in `docs/STREAMING_PROTOCOL.md`.

### Phase 2 — The gateway exists (Phoenix + Absinthe + Ecto, synchronous chat)
**Deliverables:**
- `gateway/` Phoenix 1.7 app with a heavily commented supervision tree; Ecto schemas + migrations + seeds for drivers/constructors/races/results from `data/`.
- Absinthe schema: Dataloader-batched `drivers`/`races`/`standings`/`nextRace` queries, **complexity + depth limits**, GraphiQL mounted.
- Conversations + messages persisted in Postgres with `Phoenix.Token` viewer scoping; `sendMessage` as a *synchronous* mutation proxying `/internal/chat` (non-streaming aggregate).
- ETS token-bucket rate limiter plug + Absinthe middleware + `rateLimitStatus` query; transport-level input validation; Telemetry + LiveDashboard baseline.
- Deployed: Fly (gateway) + Supabase (Postgres). ExUnit coverage for contexts and resolvers; `gateway.yml` CI green.

**Demoable:** public GraphiQL session — standings query (Dataloader, real F1 data, zero AI), `startConversation`, `sendMessage` round-trip through LangGraph.

### Phase 3 — Lights out: end-to-end streaming (the OTP centerpiece)
**Deliverables:**
- `Conversation.Server` GenServers under DynamicSupervisor + Registry: hydration, capped replay buffer, idle timeout/hibernate.
- StreamRunner under Task.Supervisor consuming agent NDJSON via Req/Finch streaming; `AgentEvent` union published through Absinthe.Subscription with micro-batched `TokenDelta`, per-message topics, subscription-time auth.
- Circuit breaker GenServer + `systemHealth` query; cache-hit, mid-stream-crash, and **reconnect/replay race** paths handled and integration-tested (tests kill the runner mid-stream); Bypass contract test replaying recorded NDJSON.
- **Transport spike (week 1):** validate `absinthe_graphql_ws` ↔ Apollo `graphql-ws` on Elixir 1.18/OTP 28 before building UI against it.
- Agent deployed to Render with bearer-token lockdown.

**Demoable:** GraphiQL subscription pane shows live `TokenDelta` + `NodeTransition` events for a `sendMessage`; docs include the kill-a-GenServer-mid-demo script.

### Phase 4 — The cockpit (React/Apollo frontend, public deploy)
**Deliverables:**
- `web/`: Apollo split-link (HttpLink + GraphQLWsLink), codegen-typed hooks, dark carbon-fiber shadcn/ui theme with the disclaimer footer.
- Streaming chat with idempotent-by-seq reducer, live pipeline-telemetry strip (NodeTransition rendering), citation chips appearing on `SourcesResolved` (before the answer finishes — "the RAG is real" moment), error/warming states with the lights-out animation.
- **Wake-on-paint** ping wired (first paint → `/up` → gateway warms agent). `nextRace` countdown, standings/calendar/driver pages from pure GraphQL.
- Deployed end-to-end: Fly + Render + Supabase + Vercel; `chatformula1.com` cut over; PR preview deploys on; `web.yml` CI green. Streamlit's funeral complete.

**Demoable:** the public site streams answers token-by-token while showing which LangGraph node is running.

### Phase 5 — Race operations (Oban, budgets, SHOWCASE, observability)
**Deliverables:**
- Oban OSS + Cron live: **nightly Jolpica/Ergast standings sync**, nightly Tavily news ingest (with Render pre-warm ping), daily conversation pruning, title generation, **SHOWCASE cache-warming job**, daily LLM-spend rollup.
- **SHOWCASE mode ships as a launch blocker:** budget ledger flips `ServiceMode`; cached answers token-replay through the identical publish path with timing histograms and the "replayed from cache" badge; `demoQuestions` chips wired in the UI; demo works with the OpenAI key removed.
- API keys (`f1s_`/SHA-256/scopes) in Postgres enforcing `triggerIngest` + LiveDashboard; account-level OpenAI spend cap set.
- PromEx metrics + public `systemStats` rendered as the frontend pit-wall panel; `wake-cron.yml` daily uptime check.
- Pinecone namespaces + deterministic IDs live via one clean `make reindex`; load test on the 256 MB machine (concurrent streams, replay-buffer memory).

**Demoable:** kill the Python service mid-stream on camera — breaker opens, UI degrades gracefully, other streams unaffected; pull the OpenAI key — SHOWCASE replays convincingly; standings updated themselves overnight.

### Phase 6 — Recruiter packaging and final cut
**Deliverables:**
- README rewritten as the 30-second sell: hero GIF of token streaming, one mermaid diagram, **"three files to read"** (`conversations/server.ex`, `schema.ex`, `graph.py`), `make setup/dev/test` quickstart, all-green CI badges, free-tier honesty notes (cold starts, budgets, what SHOWCASE means).
- `docs/` finalized: ARCHITECTURE (supervision-tree diagram + `:observer` screenshot), STREAMING_PROTOCOL, GRAPHQL, DEPLOYMENT, six ADRs including ADR-000 single-node invariants.
- Honest framing audit: the README describes exactly what runs — a routed RAG pipeline with LLM-flag routing, not a tool-calling agent; `systemStats` exposes only telemetry-fed numbers.
- Branding cleanup: every `F1-Slipstream` remnant eradicated; LICENSE + disclaimer audit; 5-minute demo script committed.

**Demoable:** a stranger clones the repo and runs the full stack locally with `docker-compose` + `mix` in under 5 minutes; the repo *is* the portfolio.

---

## Repo Hygiene Actions

### Delete outright (Phase 1 unless noted)
| Path | Reason |
|---|---|
| `src/ui/` (Streamlit app + components) | Replaced by React/Apollo |
| `tests/test_ui_components.py`, `tests/test_functionality_preservation.py` (~1,540 lines) | Test the deleted UI |
| `src/agent/nodes.py` (834 lines) | Unwired parallel implementation — salvage ContextScore ranking first |
| `src/agent/memory.py` | Orphaned; `checkpointer.put` API-incompatible |
| `src/tools/f1_tools.py` | Tools never bound to any LLM; `predict_race_outcome` contains no LLM call — shipping it misrepresents the architecture |
| `src/prompts/rag_prompts.py`, `src/prompts/specialized_prompts.py` (~900 lines) | Zero imports outside the package |
| `state.py`: `SearchDecision`, `PredictionOutput`, `ConversationContext`, `validate_state`, `create_initial_state` | Unused by the running pipeline |
| `src/utils/free_tier_limiter.py` | Zero imports anywhere — documentation theater |
| `src/security/request_signing.py` | Test-only; gateway→agent auth uses a bearer token + network posture |
| `src/security/middleware.py` `InputValidationMiddleware` + `AuthenticationMiddleware` | Never registered; superseded by gateway plugs |
| `src/api/main.py` background task queue (lines 34–186) | Never called by any route |
| `src/api/routes/admin.py` dashboards, metrics endpoints, API-key CRUD, `/config*`, `/metrics/reset` | Unauthenticated liability; replaced by PromEx + GraphQL + gateway-enforced keys |
| `GET /api/chat/sessions` (and the session-API shape generally) | Cross-tenant session enumeration / IDOR — must not be ported |
| `src/utils/dashboard.py`, `src/utils/metrics.py` collector | Metrics endpoints that no code path feeds |
| `readme.html` (28 KB marketing mockup) | Not a readme; confusing in a portfolio repo |
| `setup.py`, `pytest.ini` | Broken shim; duplicate config shadowing pyproject |
| `.github/workflows/ci.yml`, **`ci-cd.yml`** (injects real API keys into unit tests on public PRs — security fix, named in notes), `deploy.yml`, `render.yaml` | Replaced by path-filtered per-app workflows |
| `docker-compose.yml` `dev` service (+ obsolete `version:` keys), `docker-compose.prod.yml` | References nonexistent `.devcontainer/Dockerfile` |
| `scripts/setup_github_actions.sh`, `.github/DEPLOY_GUIDE.md` | Obsolete |
| `isort` from runtime dependencies; deprecated top-level `[tool.ruff]` config | Toolchain hygiene |

### Move / transform
| From | To |
|---|---|
| `src/agent/graph.py`, trimmed `state.py`, `F1_EXPERT_SYSTEM_PROMPT` | `agent/src/chatf1_agent/` (fixed, tagged, compiled-once) |
| `src/vector_store/manager.py`, `src/search/tavily_client.py`, `src/utils/cache.py` | `agent/src/chatf1_agent/retrieval/` + `caching.py` |
| Prompt-injection heuristics from `src/security/input_validation.py` | `agent/src/chatf1_agent/guards.py` (LLM-adjacent); transport-level checks reimplemented in Absinthe input objects |
| `src/ingestion/*` + CLI | `agent/ingestion/` — deterministic IDs, persisted dedup state, MD5→SHA-256 in `document_processor._hash_document` |
| `data/drivers.json`, `data/races.json` | Gateway Ecto seeds (structured GraphQL truth); `historical_features.csv` stays agent-side for RAG |
| Rate limiting / API-key / session / validation / CORS / request-ID semantics | Reimplemented in `gateway/` (behavioral contracts kept: dual windows, 429 + Retry-After, `f1s_` key format, hash-at-rest, scopes) |
| Existing `Dockerfile` builder/production stages, `Makefile` skeleton, `conftest.py` mock factories | Reused in `agent/` and repo root |
| Salvageable tests (security, prompts, processor, loader, fallback, graph/vector integration) | `agent/tests/` — `test_config.py` rename assertion fixed; `test_tavily_client.py` rewritten against the new client |

### Docs to rewrite
- **Rewrite:** `README.md` (hero GIF, three-files-to-read), `ARCHITECTURE.md`, `DEPLOYMENT.md` — all premised on the new topology.
- **New:** `STREAMING_PROTOCOL.md` (the frozen interface), `GRAPHQL.md`, `docs/adr/` (six ADRs).
- **Delete/archive:** `GITHUB_ACTIONS.md`, `tests/README.md` (stale paths, wrong counts, nonexistent markers), old `API.md` ("Coming Soon" WebSockets), `OBSERVABILITY.md`/`SECURITY.md` content folded into per-service docs; `TAVILY_INTEGRATION.md` and `SECRETS_MANAGEMENT.md` updated and kept.
- **Naming:** one pass eradicating `F1-Slipstream` from container names, CI tags, tests, and docs.

---

## Risks & Mitigations

| # | Risk | Mitigation |
|---|---|---|
| 1 | **Apollo ↔ Absinthe transport:** `@absinthe/socket` is effectively unmaintained; the plan depends on `absinthe_graphql_ws` speaking standard `graphql-ws`. | Primary choice made decisively (`absinthe_graphql_ws`); validated in a Phase 3 week-1 spike *before* any UI is built. Fallback: raw Phoenix Channels + a thin custom Apollo link. |
| 2 | **Free-tier cold starts:** Render agent sleeps (~30–60 s); a recruiter hitting the demo cold sees a wait. | Wake-on-paint choreography overlaps the cold start with landing-page reading; `WARMING_UP` events render as polished pit-radio UX (a first-class design pass, not an error path); circuit breaker prevents hangs; `demoQuestions` chips hit pre-warmed SHOWCASE answers and stream instantly regardless. |
| 3 | **Postgres provider trap:** Neon's ~190 free compute-hours/month die in ~8 days under an always-on Oban-polling gateway. | Supabase chosen (no compute-hour meter); decision frozen in ADR-003 so nobody swaps providers casually; daily Oban heartbeat defeats Supabase's 7-day pause; tuned-Neon fallback documented. |
| 4 | **Public LLM endpoint = open wallet:** public GraphiQL + a resume URL gets scraped. | Defense in depth, all shipped as Phase 5 launch blockers: ETS rate limiter (per viewer token + IP) → 2000-char input cap → daily USD ledger → SHOWCASE replay (graceful, demoable degradation, never a quota error) → account-level OpenAI billing cap → gpt-4o-mini default. A determined abuser ends the day in SHOWCASE mode — graceful, not broken. |
| 5 | **BEAM memory on 256 MB Fly:** per-token publishes + replay buffers under concurrent streams. | Micro-batching (40 ms/12 tokens), 32 KB replay-buffer cap per message, `+hmqd off_heap`, capped Finch pool; Phase 5 load test. Worst case: 512 MB tier (~$3/mo) documented as the single permitted constraint break. |
| 6 | **Fly free-allowance drift** (new orgs get trial credits, not perpetual free). | Verify current pricing before Phase 2 deploy and record in DEPLOYMENT.md; design is host-portable — the wake/warming UX already tolerates Render's spin-down, so the gateway can fall back to a Render service with the bearer token becoming load-bearing. |
| 7 | **LangGraph/LangChain version churn** (already biting: deprecated TavilySearchResults, legacy `astream_events` v1, broken checkpointer signature in dead code). | Phase 1: exact pins, `astream_events` v2 migration, `langchain-tavily`; the NDJSON protocol is the frozen interface with contract tests on **both** sides, so upstream bumps fail loudly at CI, not silently in the gateway stream. |
| 8 | **Reconnect double-delivery:** replay-buffer + live-publish overlap can duplicate `TokenDelta`s. | Seq numbers + idempotent-by-seq frontend reducer + an explicit subscription integration test for the reconnect race. Scope valve: if Phase 3 slips, cut replay to refetch-on-reconnect (final message always in Postgres). |
| 9 | **Pinecone Starter fragility:** single free region, inactivity-deletion precedent, random-ID duplication on re-ingest. | Deterministic content-hash IDs + namespaces land *before* any re-ingestion; `make reindex` rebuilds the whole index from `data/` in one command — the vector store is cattle, not a pet. |
| 10 | **Single-node invariants silently break at node #2:** ETS limiter, local PubSub fan-out, replay buffers, in-proc Python caches, `Oban.Notifiers.PG`. | ADR-000 documents every invariant; machine count pinned to 1 in `fly.toml`; revisiting it is an explicit, written decision. |
| 11 | **Scope creep — the portfolio killer:** the dead v1 code (tool layer, dashboards, key CRUD, request signing) was all plausible-looking ambition that rotted. | Each phase's "demoable in 5 minutes" gate is the enforcement mechanism; no clustering, Redis, multi-region, auth/users, or tool-calling-agent rewrite — anything off the showcase inventory (ARCHITECTURE.md §5) is cut by default. |
| 12 | **Honesty/credibility debt inherited from v1:** metrics that lied, an "agent" that is a routed RAG pipeline. | README states exactly what runs; `systemStats` exposes only telemetry-fed numbers; SHOWCASE replays carry a visible "replayed from cache" badge; Phase 6 includes an explicit honest-framing audit. A code-reading reviewer who finds theater loses all trust — so there is none. |
| 13 | **CI baseline is red today** (435 ruff issues, stale tests, `ENVIRONMENT='test'` rejected by Settings, secret-injecting workflow). | Phase 1 builds green from scratch — no workflow is ported; import-time `Settings()` is broken apart first; dummy keys only in CI, forever; toolchain pins unified (ruff/black/mypy across pyproject, pre-commit, CI). |
| 14 | **Jolpica/Ergast is a community API that could lapse.** | Standings sync degrades gracefully (last-synced timestamp surfaced in `systemStats`); seeds remain hand-refreshable; the structured-data showcase never depends on the sync succeeding on any given night. |

---

*Build order is fixed. Two non-negotiable launch blockers: the replay buffer ships capped with a tested idempotent reducer (or is cut to refetch-on-reconnect), and SHOWCASE mode ships before the URL goes on a resume.*
# The 5-Minute Demo

The exact click-path and talking points. Written for the local stack;
every beat works identically against a deployed instance (swap
`localhost` for the public hostnames).

## Pre-flight (before anyone is watching)

```bash
make db                                  # postgres:16
make setup                               # all three apps
cd gateway && mix run priv/repo/seeds.exs && cd ..

# Terminal 1 — agent (needs real keys in agent/.env for live answers):
make dev                                 # postgres + agent via Docker

# Terminal 2 — gateway, inside IEx (needed for the kill demos):
cd gateway && iex -S mix phx.server

# Terminal 3 — frontend:
make dev-web                             # http://localhost:5173
```

Warm the SHOWCASE cache while the system is LIVE (one-time, spends a
few cents — fills the seeded demo questions with real answers and
timing histograms). In the gateway IEx session:

```elixir
Oban.insert!(ChatF1.Workers.WarmShowcaseCache.new(%{}))
```

Open three browser tabs: the app (`localhost:5173`), GraphiQL
(`localhost:4000/graphiql`), and a second app tab for the isolation
beat.

---

## Beat 1 — Streaming chat with live pipeline telemetry (0:00–1:00)

**Do:** type "Who won the last race?" in the chat.

**Point at:**
- The telemetry strip above the chat: ANALYZE → ROUTE → RETRIEVE →
  RANK → GENERATE → FORMAT lighting up in sequence. Those are
  `NodeTransition` events from the actual LangGraph nodes, not an
  animation.
- Citation chips appearing **before** the answer text finishes —
  `SourcesResolved` is emitted after ranking, ahead of the first token.
  The RAG is real; you can see retrieval complete before generation.
- **Say:** "The mutation returns in under 50 ms — everything after that
  arrives on a GraphQL subscription fed by a per-conversation GenServer.
  Tokens are micro-batched, 40 milliseconds or 12 tokens per publish."

## Beat 2 — Kill the agent mid-stream (1:00–2:00)

**Do:** ask another question; while tokens are streaming, kill the
Python service:

```bash
docker stop chatf1-agent
```

**Point at:**
- The streaming bubble fails cleanly with a retryable error — no hang,
  no half-rendered junk.
- The status badge flipping as the circuit breaker counts failures and
  opens (pushed over the `systemHealthChanged` subscription, no
  polling).
- **Say:** "The stream runner is a monitored task; its `:DOWN` message
  marks the message failed and publishes a normalized error. The
  breaker now short-circuits new requests in under a millisecond
  instead of stacking timeouts."

**Do:** `docker start chatf1-agent` — the breaker half-opens, probes
`/internal/health`, and recovery is visible in the badge.

## Beat 3 — The raw stream in GraphiQL (2:00–3:00)

**Do:** in GraphiQL, run `mutation { startConversation { id } }`, then
`sendMessage`, then paste the `AgentStream` subscription from
[GRAPHQL.md](GRAPHQL.md) into the subscription pane with the returned
`assistantMessageId`.

**Point at:** raw `AgentEvent` union frames — `NodeTransition`,
`SourcesResolved`, `TokenDelta` batches with their `seq` numbers,
`MessageCompleted`.

**Say:** "Standard `graphql-ws`, so stock Apollo works. Subscriptions
are authorized at subscribe time against the viewer token — you cannot
subscribe to someone else's message. The seq numbers are what make
reconnect replay idempotent."

## Beat 4 — Standings: the zero-AI GraphQL showcase (3:00–3:30)

**Do:** open the Standings page; then in GraphiQL run the standings
query selecting `driver { constructor { name } }`.

**Say:** "Pure Postgres + Dataloader — driver→constructor batching
means a constant number of SQL queries for the whole table, refreshed
nightly by an Oban job from the Jolpica API. Zero LLM cost."

**Optional flex:** run the pathological nest
`{ drivers { results { race { results { driver { code } } } } } }` —
rejected before execution: "complexity is 19680, maximum is 400."

## Beat 5 — The pit wall (3:30–4:00)

**Do:** open the LIVE badge → pit-wall panel.

**Point at:** mode, breaker state, active conversations, BEAM process
count, p95 first-token latency, today's LLM spend against the $2
budget.

**Say:** "Every number is telemetry-fed — the fields are null until
real streams produce data. There is no theater in this panel; that is
a project rule."

## Beat 6 — Pull the budget: SHOWCASE mode (4:00–4:40)

**Do:** exhaust today's budget for real:

```bash
cd gateway && mix run -e "ChatF1.Budget.set_spent(Date.utc_today(), Decimal.new(\"2.00\"))"
```

Then click one of the demo-question chips.

**Point at:**
- The mode badge flipping to SHOWCASE.
- The answer streaming **with the same pacing as the original
  generation** — replayed from the cached answer's recorded token-timing
  histogram, through the identical publish path.
- The visible "replayed from cache" badge on the message.

**Say:** "When the daily ledger is spent — or the agent is down — the
demo degrades to cached replay instead of a quota error. It never
pretends to be live: every replayed message is marked, structurally."

**Reset afterwards:**

```bash
cd gateway && mix run -e "ChatF1.Budget.set_spent(Date.utc_today(), Decimal.new(\"0\"))"
```

## Beat 7 — Kill a GenServer on camera (4:40–5:00)

**Do:** with a stream running in tab 1 and a second conversation open
in tab 2, in the gateway IEx session:

```elixir
# List the live per-conversation servers (conversation_id → pid):
Registry.select(ChatF1.ConvRegistry, [{{:"$1", :"$2", :_}, [], [{{:"$1", :"$2"}}]}])

# Kill the one that is streaming:
{conv_id, pid} = hd(Registry.select(ChatF1.ConvRegistry, [{{:"$1", :"$2", :_}, [], [{{:"$1", :"$2"}}]}]))
Process.exit(pid, :kill)
```

**Point at:** tab 1's stream fails with a clean error; tab 2 keeps
working untouched.

**Say:** "One process per conversation under a DynamicSupervisor —
crash isolation is user-visible, not a slide."

**Encore, if asked about the supervision tree:**

```elixir
Process.whereis(ChatF1.ConvRegistry) |> Process.exit(:kill)
```

The `:rest_for_one` pipeline supervisor restarts the Registry **and**
cascades to the conversation supervisor (stale registrations would be
worse than a clean restart) — while the rate limiter, Finch pool, and
endpoint never blink. The annotated tree is in
[`gateway/lib/chat_f1/application.ex`](../gateway/lib/chat_f1/application.ex).

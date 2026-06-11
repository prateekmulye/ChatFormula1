# ADR-000: Single-node invariants

- **Status:** Accepted
- **Date:** 2026-06-10

## Context

The gateway runs on one 256 MB Fly machine. Several core mechanisms are
deliberately built on node-local state because, at portfolio scale, the
distributed alternative buys nothing and costs complexity (or money):

| Mechanism | Node-local state |
|---|---|
| Rate limiter | ETS token-bucket table owned by `ChatF1.RateLimit.Server` |
| Subscription fan-out | `Phoenix.PubSub` PG2 — local, no Redis |
| Conversation processes | `Registry` + `DynamicSupervisor` — names resolve on this node only |
| Replay buffers | In-process GenServer memory (32 KB cap per message) |
| Telemetry stats | `:chatf1_stats` ETS table feeding `systemStats` |
| Oban notifications | `Oban.Notifiers.PG` (also pooler-safe with Supabase) |
| Agent caches | In-process TTL caches in the single Python replica |

None of these breaks loudly at machine #2. They break *silently*: rate
limits double, subscribers on the wrong node stop receiving events,
reconnecting clients miss replay buffers, cache hit rates halve. That
failure mode — plausible-looking but wrong — is exactly the credibility
debt this project exists to avoid (ROADMAP risk #10).

## Decision

The system is **single-node by declaration, not by accident**:

1. Machine count is pinned to 1 (`min_machines_running = 1`, no
   autoscaling, `fly scale count 1` — see DEPLOYMENT.md §4).
2. Every mechanism in the table above is allowed to assume one node.
   No Redis, no clustering, no distributed Registry — cut by default.
3. Revisiting this is an explicit, written decision: superseding this
   ADR is the required first step of any multi-node work.
4. If the 256 MB machine is insufficient under load, the one permitted
   constraint break is vertical: the 512 MB tier (~$3/mo).

## Consequences

- Zero distributed-systems machinery to build, test, or pay for; the
  OTP design (per-conversation GenServers, replay buffers, ETS) stays
  simple and inspectable.
- Horizontal scaling is impossible without revisiting this document —
  which is the point. The invariants are written down where a future
  contributor will trip over them, instead of discovered in production.
- A machine restart loses hot state by design: conversations hydrate
  from Postgres, buffers rebuild, the limiter resets. Everything that
  must survive lives in Postgres.

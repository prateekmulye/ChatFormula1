# ADR-006: Hand-rolled ETS rate limiter, deliberately not Hammer

- **Status:** Accepted
- **Date:** 2026-06-10

## Context

Every public GraphQL operation needs rate limiting — it is the first
layer of the open-wallet defense (ROADMAP risk #4) and v1's most
embarrassing gap (a `FreeTierLimiter` module existed but was imported
by nothing). Off-the-shelf Elixir options exist: Hammer, ExRated,
PlugAttack.

But this is a portfolio repo. A dependency that hides the interesting
mechanism — atomic check-and-consume, window expiry, the ETS
concurrency model — removes exactly the code a reviewing engineer
would want to read. The requirements are also small enough to own:
single node (ADR-000), two windows, one keying scheme.

## Decision

A hand-rolled **dual-window token bucket** in `ChatF1.RateLimit`:

- A `GenServer` (`RateLimit.Server`) owns a `public` ETS table.
  **Writes are serialized through the GenServer** for atomic
  check-and-consume; **reads are direct ETS lookups** on the hot path —
  the standard BEAM split between safe mutation and zero-copy reads.
- Two windows per key: per-minute (burst control) and per-hour
  (sustained abuse). Keys are the viewer token, falling back to IP.
- Enforcement at two layers: a Plug (transport) and an Absinthe
  middleware on every root query/mutation field (one token per
  operation; subscriptions are gated at subscribe time instead of
  per-event).
- Denials carry `RATE_LIMITED` plus a `retry_after` extension;
  telemetry fires on allow/deny; clients can self-inspect via the
  public `rateLimitStatus` query.

"I built it" is the point — the limiter is meant to be read,
questioned, and defended in an interview.

## Consequences

- ~290 lines of owned code (server + plug + middleware) with its own
  test suite, instead of a dependency; bugs are ours, but so is the
  understanding.
- Node-local by design: limits do not survive restarts and would
  silently double at machine #2 — accepted and documented in ADR-000.
- The limiter is observable end-to-end: ETS state, telemetry events,
  and a GraphQL query all expose the same numbers, which keeps the
  "no theater" rule auditable.

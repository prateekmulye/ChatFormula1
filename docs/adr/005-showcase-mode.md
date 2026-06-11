# ADR-005: SHOWCASE mode — cached replay as graceful degradation

- **Status:** Accepted
- **Date:** 2026-06-10

## Context

Two facts collide:

1. **A public LLM endpoint on a resume is an open wallet** (ROADMAP
   risk #4). A public GraphiQL plus a scraped URL can drain any budget.
2. **A recruiter at 3 a.m. must always see a streaming demo.** A quota
   error, a dead spinner, or a hung request reads as a broken project,
   no matter how good the error handling prose is.

Hard spend caps alone solve #1 by causing #2. The demo needs a
degradation path that still *demonstrates the system*.

## Decision

A `ServiceMode` (`LIVE | DEGRADED | SHOWCASE`), computed from two real
signals — the daily USD budget ledger in Postgres and the circuit
breaker state. Composition rule: SHOWCASE > DEGRADED > LIVE.

When mode is SHOWCASE (budget spent or agent down):

- A nightly Oban job (`WarmShowcaseCache`) has pre-generated answers
  for every `demoQuestions` entry via the real pipeline, storing
  content, sources, the node-transition trace, and the **original
  token-timing histogram**.
- `Conversation.Server` skips Python and token-replays the cached
  answer **through the identical publish path** — real `TokenDelta`s
  paced by the recorded delays, `SourcesResolved`, then
  `MessageCompleted{cached: true}`. The frontend render path cannot
  tell the difference, because there is no second path.
- Free-text questions match the nearest cached answer via `pg_trgm`
  similarity (threshold 0.3); below threshold the client gets an honest
  `AgentError{BUDGET_EXHAUSTED}` rather than a wrong answer.

**The honesty guarantee is structural:** every replay carries
`NodeTransition{REPLAYING_CACHE}` and `cached: true`, and the UI
renders a visible "replayed from cache" badge. SHOWCASE never
impersonates live inference (ROADMAP risk #12).

## Consequences

- A determined abuser ends the day in SHOWCASE mode — the demo
  degrades gracefully instead of breaking or spending.
- The demo works with the OpenAI key removed entirely; this is a demo
  beat, not an apology (see DEMO.md).
- Costs carried: an answers table, a warming job, a replayer module,
  and the mode gate in `Conversation.Server` — all small, all tested.
- The cache must be warmed before it is needed; the warming job
  skips itself when already in SHOWCASE (it cannot spend budget that
  is gone), so an operator who never lets it run LIVE gets the
  `BUDGET_EXHAUSTED` fallback, not silence.

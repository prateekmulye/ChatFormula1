# ADR-001: Two services — Elixir gateway + Python inference engine

- **Status:** Accepted
- **Date:** 2026-06-10

## Context

v1 was a single Python service (FastAPI + Streamlit) that accumulated
dead layers: an unused tool framework, unenforced auth middleware,
metrics nobody fed, in-memory sessions that died on restart. The v2
goal is a portfolio that shows real engineering depth across
**Elixir/OTP, GraphQL, and AI** — and the AI ecosystem (LangGraph,
LangChain, Pinecone clients) is Python-first, while everything the
application actually needs to *be* — stateful, concurrent, supervised,
cheap to keep always-on — is what the BEAM is for.

One-language alternatives were considered and rejected:

- **All Python:** no OTP story, and v1 already demonstrated where
  Python-monolith state management ends up (restart-loss, IDOR-shaped
  session handling).
- **All Elixir:** reimplementing the RAG pipeline against immature
  Elixir LLM tooling makes the AI layer the project's risk center
  instead of its supporting act.

## Decision

Two services with a hard ownership boundary (ARCHITECTURE §2):

- **The Elixir gateway IS the application.** It owns the entire public
  surface (GraphQL), all state (Postgres + GenServers), identity, rate
  limiting, budgets, scheduling, and telemetry.
- **Python is a stateless inference engine.** One internal NDJSON
  endpoint; history arrives in the payload; no sessions, no
  checkpointer, no public routes. It keeps only the load-bearing parts:
  the LangGraph pipeline, retrieval, guards, caches.
- The boundary is the **frozen NDJSON protocol** (STREAMING_PROTOCOL.md,
  [ADR-003](003-ndjson-over-sse.md)) with contract tests on both sides.

Exactly two backend services — not three, not a worker fleet. The
constraint is part of the design (free-tier hosting, ADR-000).

## Consequences

- The gateway treats LLM work as an untrusted upstream: circuit
  breaker, budget ledger, and SHOWCASE fallback all live on the Elixir
  side and work even when Python is asleep or gone.
- Two deploys, two toolchains, two CI pipelines (plus web) — priced in;
  path-filtered workflows keep CI cheap.
- Cross-service streaming latency and Render cold starts become part of
  the product: the warming UX and wake-on-paint choreography exist
  because of this split.
- Either side can be rewritten behind the protocol (the contract tests
  are the safety net) — which already paid off when the provider seam
  made the agent model-agnostic ([ADR-002](002-model-agnostic-providers.md)).

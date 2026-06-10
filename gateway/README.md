# gateway/ — Phoenix GraphQL Gateway (coming in Phase 2)

This directory will hold the **Elixir 1.18 / Phoenix 1.7 / Absinthe**
gateway — the only public backend and the application's center of gravity:
the GraphQL surface (queries, mutations, subscriptions), conversation
persistence, per-conversation GenServers with replay buffers, rate
limiting, budget enforcement, Oban background jobs, and telemetry.

It lands in **Phase 2** (synchronous chat) and **Phase 3** (end-to-end
streaming) of the migration plan — see
[docs/ROADMAP.md](../docs/ROADMAP.md) and
[docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md).

defmodule ChatF1.Application do
  @moduledoc """
  OTP application entry point for the ChatFormula1 gateway.

  ## Supervision tree (Phase 5)

  All top-level children run under a `:one_for_one` supervisor.  The three
  conversation-pipeline processes (`ConvRegistry`, `ConversationSupervisor`,
  `StreamTaskSupervisor`) are grouped under a dedicated `:rest_for_one`
  supervisor so a `ConvRegistry` crash cascades only to the DynamicSupervisor
  — which must re-register its children on restart.

  ```
  ChatF1.Supervisor  [:one_for_one]
  ├── ChatF1.Repo                       Ecto.Repo — Postgres connection pool
  ├── {DNSCluster, ...}                 DNS-based peer discovery (no-op, ADR-000)
  ├── {Phoenix.PubSub, ...}             Local PG2 PubSub (no Redis, ADR-000)
  ├── {Finch, name: ChatF1.Finch}       HTTP pool for agent proxy calls
  ├── ChatF1.RateLimit.Server           ETS token-bucket GenServer
  ├── ChatF1Web.Telemetry               Telemetry supervisor
  ├── ChatF1.Telemetry.PromEx           Prometheus metrics exporter (Phase 5)
  ├── ChatF1.Agents.Breaker             Circuit breaker GenServer (Phase 3)
  ├── {Oban, ...}                       Background jobs + cron (Phase 5)
  ├── ChatF1.ConvPipelineSupervisor     [:rest_for_one] (Phase 3)
  │   ├── {Registry, name: ChatF1.ConvRegistry}
  │   │     Per-conversation lookup; via-tuple process registration.
  │   │     `:rest_for_one` ensures a registry crash cascades to the
  │   │     DynamicSupervisor, which re-registers its children on restart.
  │   ├── {DynamicSupervisor,           One supervisor per conversation.
  │   │     name: ChatF1.ConversationSupervisor}
  │   └── {Task.Supervisor,             Supervised streaming workers.
  │         name: ChatF1.StreamTaskSupervisor}
  └── ChatF1Web.Endpoint                Phoenix HTTP + WS endpoint
  ```

  ### Why `:rest_for_one` for the conversation pipeline?

  * `ConvRegistry` is the naming anchor for `Conversation.Server`s.  If the
    registry crashes, all via-tuple lookups break until it restarts, so the
    DynamicSupervisor must also restart (killing all in-flight conversations
    cleanly rather than leaving orphan processes with stale registration).
  * `StreamTaskSupervisor` depends on `ConversationSupervisor` being alive
    (tasks cast to their owning server), so it also cascades.
  * The `[:rest_for_one]` sub-supervisor keeps this failure domain isolated:
    a single broken conversation never affects `RateLimit.Server`, `Finch`,
    or the `Endpoint`.

  ### Phase-5-specific design notes

  * `Oban` uses `Oban.Notifiers.PG` (pooler-safe, single-node, no Redis).
    Machine count is pinned to 1 in fly.toml (ADR-000).
  * `ChatF1.Telemetry.PromEx` starts before the Endpoint so metrics collection
    begins before the first request arrives.
  * ETS `:chatf1_stats` table is created at startup by
    `ChatF1.Telemetry.StatsHandler.attach/0`.
  """

  use Application

  @impl true
  def start(_type, _args) do
    # Attach telemetry stats handler and create ETS table for systemStats.
    ChatF1.Telemetry.StatsHandler.attach()

    children = [
      # ── Ecto repo ────────────────────────────────────────────────────────────
      ChatF1.Repo,

      # ── DNS cluster ──────────────────────────────────────────────────────────
      {DNSCluster, query: Application.get_env(:chat_f1, :dns_cluster_query) || :ignore},

      # ── Phoenix PubSub ───────────────────────────────────────────────────────
      # Absinthe.Subscription uses this for subscription fan-out.
      # Single-node invariant (ADR-000): no Redis, no distributed PubSub.
      {Phoenix.PubSub, name: ChatF1.PubSub},

      # ── Finch HTTP pool ──────────────────────────────────────────────────────
      {Finch, name: ChatF1.Finch},

      # ── Rate-limit GenServer ─────────────────────────────────────────────────
      ChatF1.RateLimit.Server,

      # ── Telemetry supervisor ─────────────────────────────────────────────────
      ChatF1Web.Telemetry,

      # ── PromEx metrics exporter (Phase 5) ────────────────────────────────────
      # Must start before Endpoint so collection begins before first request.
      ChatF1.Telemetry.PromEx,

      # ── Circuit breaker (Phase 3) ─────────────────────────────────────────────
      # Must start before ConversationSupervisor so begin_stream calls can
      # always check breaker state.
      ChatF1.Agents.Breaker,

      # ── Oban background jobs + cron (Phase 5) ────────────────────────────────
      # Notifier: PG (single-node pooler-safe, ADR-000).
      # Queue config and cron schedule live in runtime.exs.
      {Oban, Application.fetch_env!(:chat_f1, Oban)},

      # ── Conversation pipeline sub-supervisor (Phase 3) ───────────────────────
      # ChatF1.ConvPipelineSupervisor uses :rest_for_one internally so a
      # ConvRegistry crash cascades to DynamicSupervisor.  See module doc.
      ChatF1.ConvPipelineSupervisor,

      # ── Phoenix Endpoint ─────────────────────────────────────────────────────
      # Bandit acceptors open after all children above are running.
      ChatF1Web.Endpoint,

      # ── Absinthe subscription registry ───────────────────────────────────────
      # Must start AFTER the endpoint (it supervises per-endpoint proxies that
      # need the endpoint's PubSub). `use Absinthe.Phoenix.Endpoint` does NOT
      # start this — without it, every GraphQL `subscribe` raises
      # "Pubsub not configured!" and the websocket closes with 1011.
      {Absinthe.Subscription, ChatF1Web.Endpoint}
    ]

    opts = [strategy: :one_for_one, name: ChatF1.Supervisor]
    Supervisor.start_link(children, opts)
  end

  @impl true
  def config_change(changed, _new, removed) do
    ChatF1Web.Endpoint.config_change(changed, removed)
    :ok
  end
end

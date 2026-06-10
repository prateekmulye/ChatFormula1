defmodule ChatF1.Application do
  @moduledoc """
  OTP application entry point for the ChatFormula1 gateway.

  ## Supervision tree (Phase 2)

  All children run under a single `:one_for_one` supervisor.  Each child is
  isolated — a crash in one does not affect siblings.  Phase 3 adds
  `ChatF1.ConversationSupervisor` (DynamicSupervisor), a per-conversation
  Registry, and a `Task.Supervisor` for streaming workers; they slot in
  between `RateLimit.Server` and `Endpoint`.

  ```
  ChatF1.Supervisor  [:one_for_one]
  ├── ChatF1.Repo                   Ecto.Repo — Postgres connection pool
  ├── {DNSCluster, ...}             DNS-based peer discovery (no-op on single node; ADR-000)
  ├── {Phoenix.PubSub, ...}         Local PubSub (PG2 transport; single node, no Redis)
  ├── {Finch, name: ChatF1.Finch}   HTTP connection pool for agent proxy calls
  ├── ChatF1.RateLimit.Server       GenServer owning the ETS token-bucket table
  ├── ChatF1Web.Telemetry           Telemetry supervisor (metrics + poller)
  └── ChatF1Web.Endpoint            Phoenix HTTP endpoint (Bandit adapter)
  ```

  ### Why this order?

  * **Repo first** — downstream processes may need DB connectivity at startup
    (seeds, warm-up queries).
  * **PubSub before Endpoint** — the endpoint registers PubSub topics on init;
    if PubSub isn't up yet, topic registration fails.
  * **Finch before RateLimit.Server** — RateLimit.Server does not use Finch,
    but placing the HTTP pool early makes all downstream processes able to make
    outbound calls the moment they start.
  * **Endpoint last** — we don't accept traffic until the full tree is healthy.
    Bandit's acceptors only open after `start_link/2` returns `:ok`.

  ### Restart strategy

  `:one_for_one` is correct here because children are independent.  The only
  dependency chain (PubSub → Endpoint) is handled by start order, not by a
  `:rest_for_one` supervisor — Phoenix tolerates transient PubSub restarts
  gracefully via its reconnect logic.

  ### Phase 3 additions (do not scaffold yet)

  * `ChatF1.ConvRegistry` — `{Registry, keys: :unique, name: ChatF1.ConvRegistry}`
  * `ChatF1.ConversationSupervisor` — `{DynamicSupervisor, name: ChatF1.ConversationSupervisor}`
  * `ChatF1.StreamTaskSupervisor` — `{Task.Supervisor, name: ChatF1.StreamTaskSupervisor}`

  These require a phase-3 supervision sub-tree with a `:rest_for_one` strategy
  so a ConvRegistry crash cascades to the DynamicSupervisor (which re-registers
  its children on restart).  See docs/ARCHITECTURE.md §5 item 2 for the full
  design.
  """

  use Application

  @impl true
  def start(_type, _args) do
    children = [
      # ── Ecto repo ────────────────────────────────────────────────────────────
      # Manages the PostgreSQL connection pool (Postgrex under the hood).
      # pool_size is set per environment; prod uses POOL_SIZE env var (default 5
      # on a 256 MB Fly machine — keep it low to avoid Supabase connection limits).
      ChatF1.Repo,

      # ── DNS cluster ──────────────────────────────────────────────────────────
      # Resolves peer nodes for Erlang distribution.  Single-node on Fly (ADR-000
      # pins machine count to 1), so this resolves to :ignore and is a no-op.
      # We keep it in the tree so the prod release config is identical to a
      # future multi-node upgrade path.
      {DNSCluster, query: Application.get_env(:chat_f1, :dns_cluster_query) || :ignore},

      # ── Phoenix PubSub ───────────────────────────────────────────────────────
      # Local PG2-backed PubSub.  Single-node invariant (ADR-000): no Redis, no
      # distributed PubSub.  Phase 3 Absinthe subscriptions publish here.
      {Phoenix.PubSub, name: ChatF1.PubSub},

      # ── Finch HTTP pool ──────────────────────────────────────────────────────
      # Connection pool used by ChatF1.Agents.Client (Req → Finch).
      # Pool size: 10 for the agent host.  On a 256 MB machine each persistent
      # connection costs ~8 KB; 10 is well under budget.
      {Finch, name: ChatF1.Finch},

      # ── Rate-limit GenServer ─────────────────────────────────────────────────
      # Creates and owns an ETS table for the dual-window token-bucket limiter.
      # Must start before the Endpoint so that the rate-limit Absinthe middleware
      # and Plug can reference the table.
      ChatF1.RateLimit.Server,

      # ── Telemetry supervisor ─────────────────────────────────────────────────
      # Attaches Phoenix, Ecto, Absinthe, and Finch telemetry handlers;
      # runs a periodic poller emitting VM metrics.
      ChatF1Web.Telemetry,

      # ── Phoenix Endpoint ─────────────────────────────────────────────────────
      # Starts the Bandit HTTP server.  Acceptors only open after all children
      # above are running — early traffic gets a TCP-level connection refused
      # rather than an application-level error, which is safer.
      ChatF1Web.Endpoint
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

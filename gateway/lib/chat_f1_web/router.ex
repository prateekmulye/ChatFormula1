defmodule ChatF1Web.Router do
  use ChatF1Web, :router

  pipeline :graphql do
    plug :accepts, ["json"]
    plug ChatF1Web.Plugs.ViewerToken
  end

  # GraphiQL serves an HTML playground but still needs the viewer pipeline so
  # playground requests are identified and rate-limited like any other client.
  pipeline :graphiql do
    plug :accepts, ["html", "json"]
    plug ChatF1Web.Plugs.ViewerToken
  end

  # API-key pipeline — for /dev/dashboard, /metrics.
  # Any valid unrevoked key with scope admin:dashboard is required.
  pipeline :api_key_dashboard do
    plug :fetch_session
    plug :protect_from_forgery
    plug ChatF1Web.Plugs.ApiKey, scope: "admin:dashboard"
  end

  pipeline :api_key_metrics do
    plug ChatF1Web.Plugs.ApiKey, scope: "admin:dashboard"
  end

  # ── GraphQL API ──────────────────────────────────────────────────────────────
  # Complexity analysis is enforced here (the schema declares per-field
  # complexity functions; this plug option is what actually rejects
  # over-budget documents). See ChatF1Web.Schema moduledoc for the budget.
  scope "/graphql" do
    pipe_through :graphql

    forward "/", Absinthe.Plug,
      schema: ChatF1Web.Schema,
      json_codec: Jason,
      analyze_complexity: true,
      max_complexity: 400
  end

  # ── GraphiQL (dev + prod — public, rate-limited via schema middleware) ────────
  # Goes through the same :graphql pipeline as the API so playground requests
  # carry a viewer token and are rate-limited like any other client.
  scope "/graphiql" do
    pipe_through :graphiql

    forward "/", Absinthe.Plug.GraphiQL,
      schema: ChatF1Web.Schema,
      json_codec: Jason,
      interface: :playground,
      analyze_complexity: true,
      max_complexity: 400
  end

  # ── LiveDashboard — API-key gated in ALL envs (replaces dev-only pipeline) ──
  # Phase 5: header x-api-key with scope admin:dashboard required.
  # This intentionally works in prod — it's a portfolio showcase dashboard.
  import Phoenix.LiveDashboard.Router

  scope "/dev" do
    pipe_through :api_key_dashboard
    live_dashboard "/dashboard", metrics: ChatF1Web.Telemetry
  end

  # ── Prometheus metrics ───────────────────────────────────────────────────────
  # Behind the same API-key scope as LiveDashboard.
  scope "/metrics" do
    pipe_through :api_key_metrics

    forward "/", PromEx.Plug, prom_ex: ChatF1.Telemetry.PromEx
  end

  # ── Health probes ─────────────────────────────────────────────────────────────
  # /up is for Fly.io health checks + wake-on-paint ping from the frontend.
  # /healthz returns 200 JSON for monitoring tools (portfolio build-probe reads keys).
  scope "/" do
    get "/up", ChatF1Web.HealthController, :up
    get "/healthz", ChatF1Web.HealthController, :healthz
  end
end

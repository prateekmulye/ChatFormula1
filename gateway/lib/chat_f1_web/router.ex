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

  # ── GraphQL API ──────────────────────────────────────────────────────────────
  scope "/graphql" do
    pipe_through :graphql

    forward "/", Absinthe.Plug,
      schema: ChatF1Web.Schema,
      json_codec: Jason
  end

  # ── GraphiQL (dev + prod — public, rate-limited via schema middleware) ────────
  # Goes through the same :graphql pipeline as the API so playground requests
  # carry a viewer token and are rate-limited like any other client.
  scope "/graphiql" do
    pipe_through :graphiql

    forward "/", Absinthe.Plug.GraphiQL,
      schema: ChatF1Web.Schema,
      json_codec: Jason,
      interface: :playground
  end

  # ── LiveDashboard (dev-only pipeline) ────────────────────────────────────────
  if Application.compile_env(:chat_f1, :dev_routes) do
    import Phoenix.LiveDashboard.Router

    scope "/dev" do
      pipe_through [:fetch_session, :protect_from_forgery]
      live_dashboard "/dashboard", metrics: ChatF1Web.Telemetry
    end
  end

  # ── Health probes ─────────────────────────────────────────────────────────────
  # /up is for Fly.io health checks + wake-on-paint ping from the frontend.
  # /healthz returns 200 JSON for monitoring tools.
  scope "/" do
    get "/up", ChatF1Web.HealthController, :up
    get "/healthz", ChatF1Web.HealthController, :healthz
  end
end

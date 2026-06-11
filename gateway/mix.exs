defmodule ChatF1.MixProject do
  use Mix.Project

  def project do
    [
      app: :chat_f1,
      version: "0.1.0",
      elixir: "~> 1.18",
      elixirc_paths: elixirc_paths(Mix.env()),
      start_permanent: Mix.env() == :prod,
      aliases: aliases(),
      deps: deps(),
      dialyzer: dialyzer()
    ]
  end

  def application do
    [
      mod: {ChatF1.Application, []},
      extra_applications: [:logger, :runtime_tools]
    ]
  end

  defp elixirc_paths(:test), do: ["lib", "test/support"]
  defp elixirc_paths(_), do: ["lib"]

  defp deps do
    [
      # Phoenix + web server
      {:phoenix, "~> 1.8.0"},
      {:phoenix_ecto, "~> 4.7"},
      {:bandit, "~> 1.12"},

      # Database
      {:ecto_sql, "~> 3.14"},
      {:postgrex, "~> 0.22"},

      # GraphQL
      {:absinthe, "~> 1.7"},
      {:absinthe_plug, "~> 1.5"},
      {:absinthe_phoenix, "~> 2.0"},
      {:dataloader, "~> 2.0"},

      # WebSocket transport for graphql-ws protocol (Apollo GraphQLWsLink)
      # Transport spike result: absinthe_graphql_ws 0.3.6 is compatible with
      # Phoenix 1.8 + Bandit via websock_adapter (already in the tree).
      # Requires absinthe_phoenix for subscription fan-out.
      {:absinthe_graphql_ws, "~> 0.3.6"},

      # HTTP client — agent proxy
      {:req, "~> 0.5"},
      {:finch, "~> 0.18"},

      # Serialization
      {:jason, "~> 1.4"},

      # Background jobs + cron (single-node, Oban.Notifiers.PG, ADR-000)
      {:oban, "~> 2.19"},

      # Telemetry + observability
      {:telemetry_metrics, "~> 1.1"},
      {:telemetry_poller, "~> 1.3"},
      {:phoenix_live_dashboard, "~> 0.8"},
      # PromEx: Phoenix/Ecto/Oban/BEAM metrics exported to Prometheus /metrics
      {:prom_ex, "~> 1.11"},

      # DNS clustering (single-node; ADR-000 pins machine count to 1)
      {:dns_cluster, "~> 0.2"},

      # Dev / test tooling
      {:bypass, "~> 2.1", only: :test},
      {:credo, "~> 1.7", only: [:dev, :test], runtime: false},
      {:dialyxir, "~> 1.4", only: [:dev, :test], runtime: false}
    ]
  end

  defp dialyzer do
    [
      plt_file: {:no_warn, "priv/plts/dialyzer.plt"},
      plt_add_apps: [:mix],
      flags: [:error_handling, :underspecs],
      ignore_warnings: ".dialyzer_ignore.exs",
      # Fail CI if an ignore entry stops matching — keeps the file honest.
      list_unused_filters: true
    ]
  end

  defp aliases do
    [
      setup: ["deps.get", "ecto.setup"],
      "ecto.setup": ["ecto.create", "ecto.migrate", "run priv/repo/seeds.exs"],
      "ecto.reset": ["ecto.drop", "ecto.setup"],
      test: ["ecto.create --quiet", "ecto.migrate --quiet", "test"]
    ]
  end
end

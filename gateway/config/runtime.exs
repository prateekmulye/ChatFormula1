import Config

# PHX_SERVER=true enables the endpoint in a Mix release.
# In dev/test the endpoint is started directly by the supervision tree.
if System.get_env("PHX_SERVER") do
  config :chat_f1, ChatF1Web.Endpoint, server: true
end

# ── Oban configuration (all envs) ────────────────────────────────────────────
# Uses Oban.Notifiers.PG (pooler-safe, no LISTEN/NOTIFY dependency).
# Machine count is pinned to 1 (ADR-000) — no global distributed locks needed.
# Cron expressions use 5-field "min hour dom mon dow" format.
config :chat_f1, Oban,
  repo: ChatF1.Repo,
  notifier: Oban.Notifiers.PG,
  queues: [default: 10],
  plugins: [
    {Oban.Plugins.Pruner, max_age: 60 * 60 * 24 * 7},
    {Oban.Plugins.Cron,
     crontab: [
       # 02:00 UTC — nightly standings/races/results sync from Jolpica
       {"0 2 * * *", ChatF1.Workers.JolpicaSync},
       # 01:00 UTC — nightly Tavily news ingest trigger
       {"0 1 * * *", ChatF1.Workers.IngestNews},
       # 03:00 UTC — daily conversation TTL pruning (7-day window)
       {"0 3 * * *", ChatF1.Workers.PruneConversations},
       # 04:00 UTC — SHOWCASE cache warming (after JolpicaSync)
       {"0 4 * * *", ChatF1.Workers.WarmShowcaseCache},
       # 23:30 UTC — daily spend rollup reconciliation
       {"30 23 * * *", ChatF1.Workers.SpendRollup}
     ]}
  ]

if config_env() == :prod do
  # DATABASE_URL — required in production.
  # Format: ecto://USER:PASS@HOST/DATABASE
  # On Fly.io with Supabase use the IPv6 direct URL; set ECTO_IPV6=true.
  database_url =
    System.get_env("DATABASE_URL") ||
      raise "environment variable DATABASE_URL is missing"

  maybe_ipv6 = if System.get_env("ECTO_IPV6") in ~w(true 1), do: [:inet6], else: []

  config :chat_f1, ChatF1.Repo,
    url: database_url,
    pool_size: String.to_integer(System.get_env("POOL_SIZE") || "5"),
    socket_options: maybe_ipv6

  # SECRET_KEY_BASE — required in production. Generate with: mix phx.gen.secret
  secret_key_base =
    System.get_env("SECRET_KEY_BASE") ||
      raise "environment variable SECRET_KEY_BASE is missing"

  host = System.get_env("PHX_HOST") || "chatformula1.com"
  port = String.to_integer(System.get_env("PORT") || "4000")

  config :chat_f1, ChatF1Web.Endpoint,
    url: [host: host, port: 443, scheme: "https"],
    http: [ip: {0, 0, 0, 0, 0, 0, 0, 0}, port: port],
    secret_key_base: secret_key_base

  # AGENT_URL — internal URL of the Python inference service (Render).
  # INTERNAL_API_TOKEN — shared bearer token; same value set in the agent env.
  config :chat_f1,
         :agent_url,
         System.get_env("AGENT_URL") || raise("environment variable AGENT_URL is missing")

  config :chat_f1,
         :internal_api_token,
         System.get_env("INTERNAL_API_TOKEN") ||
           raise("environment variable INTERNAL_API_TOKEN is missing")

  # CORS_ORIGINS — comma-separated browser origins allowed to call the
  # GraphQL API (the Vercel frontend), e.g. "https://chatformula1.com".
  # Empty default: no cross-origin browser access until explicitly granted.
  config :chat_f1,
         :cors_origins,
         (System.get_env("CORS_ORIGINS") || "")
         |> String.split(",", trim: true)
         |> Enum.map(&String.trim/1)
end

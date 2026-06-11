import Config

config :chat_f1, ChatF1.Repo,
  username: System.get_env("PGUSER") || "postgres",
  password: System.get_env("PGPASSWORD") || "postgres",
  hostname: System.get_env("PGHOST") || "localhost",
  database: "chatf1_test#{System.get_env("MIX_TEST_PARTITION")}",
  pool: Ecto.Adapters.SQL.Sandbox,
  pool_size: System.schedulers_online() * 2

config :chat_f1, ChatF1Web.Endpoint,
  http: [ip: {127, 0, 0, 1}, port: 4002],
  secret_key_base: "MxKELPtS5JbKbW8EGoLg4bOpRIyVYWrPgQ4oSuGnnrAcmuzcm8i7st/OvnRJtjC/",
  server: false

# Agent URL is set per-test by Bypass; this default is a stub.
config :chat_f1, :agent_url, "http://localhost:9999"
config :chat_f1, :internal_api_token, "test-token"

# Oban: inline testing mode — jobs are executed synchronously in tests.
# Cron plugin disabled in tests (no scheduled side effects).
config :chat_f1, Oban,
  repo: ChatF1.Repo,
  notifier: Oban.Notifiers.PG,
  queues: false,
  plugins: false,
  testing: :inline

# PromEx: disable DB-polling plugins in tests to avoid Ecto sandbox ownership errors.
# The PromEx poller process is not in the sandbox and cannot checkout DB connections.
config :chat_f1, :prom_ex_db_plugins, false

config :chat_f1, ChatF1.Telemetry.PromEx,
  manual_metrics_start_delay: :no_delay,
  drop_metrics_groups: [],
  grafana: :disabled,
  metrics_server: :disabled

config :logger, level: :warning
config :phoenix, :plug_init_mode, :runtime

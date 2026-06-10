import Config

# Dev Postgres — uses the local Postgres instance.
# Username/password can be overridden via DATABASE_URL in runtime.exs.
# The docker-compose postgres:16 also works when running `make db`.
config :chat_f1, ChatF1.Repo,
  username: System.get_env("PGUSER") || "postgres",
  password: System.get_env("PGPASSWORD") || "postgres",
  hostname: System.get_env("PGHOST") || "localhost",
  database: "chatf1_dev",
  stacktrace: true,
  show_sensitive_data_on_connection_error: true,
  pool_size: 10

config :chat_f1, ChatF1Web.Endpoint,
  http: [ip: {127, 0, 0, 1}, port: String.to_integer(System.get_env("PORT") || "4000")],
  check_origin: false,
  code_reloader: true,
  debug_errors: true,
  secret_key_base: "zf3VbyJdef5mFNpgbhRcFKkVSCkYIq6CvTNlmK1ZJFrxeK1RfG/g40cPEAcoocYL",
  watchers: []

# Dev routes enable LiveDashboard at /dev/dashboard (dev-only pipeline).
config :chat_f1, dev_routes: true

# Agent service defaults for local dev.
# Override by setting AGENT_URL and INTERNAL_API_TOKEN env vars.
config :chat_f1, :agent_url, System.get_env("AGENT_URL") || "http://localhost:8000"

config :chat_f1,
       :internal_api_token,
       System.get_env("INTERNAL_API_TOKEN") || "dev-token-not-a-secret"

config :logger, :default_formatter, format: "[$level] $message\n"
config :phoenix, :stacktrace_depth, 20
config :phoenix, :plug_init_mode, :runtime

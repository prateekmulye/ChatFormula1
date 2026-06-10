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

config :logger, level: :warning
config :phoenix, :plug_init_mode, :runtime

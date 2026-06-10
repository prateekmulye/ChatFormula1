import Config

config :chat_f1,
  ecto_repos: [ChatF1.Repo],
  generators: [timestamp_type: :utc_datetime]

config :chat_f1, ChatF1Web.Endpoint,
  url: [host: "localhost"],
  adapter: Bandit.PhoenixAdapter,
  render_errors: [
    formats: [json: ChatF1Web.ErrorJSON],
    layout: false
  ],
  pubsub_server: ChatF1.PubSub

# Viewer token signing salt — non-secret; the secret_key_base is the secret.
config :chat_f1, :viewer_token_salt, "chatf1_viewer_v1"
# Viewer token max age in seconds (30 days)
config :chat_f1, :viewer_token_max_age, 2_592_000

# Rate limiter: dual-window token bucket per viewer token.
# Phase 5 wires these to runtime config; sensible defaults for Phase 2.
config :chat_f1, :rate_limit,
  per_minute: 20,
  per_hour: 200

config :logger, :default_formatter,
  format: "$time $metadata[$level] $message\n",
  metadata: [:request_id]

config :phoenix, :json_library, Jason

import_config "#{config_env()}.exs"

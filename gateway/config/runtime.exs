import Config

# PHX_SERVER=true enables the endpoint in a Mix release.
# In dev/test the endpoint is started directly by the supervision tree.
if System.get_env("PHX_SERVER") do
  config :chat_f1, ChatF1Web.Endpoint, server: true
end

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
end

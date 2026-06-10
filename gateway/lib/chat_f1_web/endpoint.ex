defmodule ChatF1Web.Endpoint do
  use Phoenix.Endpoint, otp_app: :chat_f1

  # Static files served from priv/static.
  plug Plug.Static,
    at: "/",
    from: :chat_f1,
    gzip: false,
    only: ChatF1Web.static_paths()

  # Code reloader — dev only, stripped by Phoenix in other envs.
  if code_reloading? do
    plug Phoenix.CodeReloader
  end

  plug Plug.RequestId
  plug Plug.Telemetry, event_prefix: [:phoenix, :endpoint]

  plug Plug.Parsers,
    parsers: [:urlencoded, :multipart, :json],
    pass: ["*/*"],
    json_decoder: Phoenix.json_library()

  plug Plug.MethodOverride
  plug Plug.Head
  plug Plug.Session, store: :cookie, key: "_chat_f1_key", signing_salt: "chatf1salt"

  plug ChatF1Web.Router
end

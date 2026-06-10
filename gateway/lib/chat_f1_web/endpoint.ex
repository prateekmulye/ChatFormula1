defmodule ChatF1Web.Endpoint do
  use Phoenix.Endpoint, otp_app: :chat_f1
  use Absinthe.Phoenix.Endpoint

  # graphql-ws WebSocket transport — Apollo GraphQLWsLink connects here.
  #
  # Mounted at WSS://<host>/socket/websocket; sub-protocol: "graphql-ws".
  # Auth: client sends connection_init with {"token": "<viewer_token>"}.
  #
  # Transport spike outcome: absinthe_graphql_ws 0.3.6 + Phoenix 1.8 + Bandit
  # is COMPATIBLE.  The library implements Phoenix.Socket.Transport directly
  # (not Phoenix Channels), so Bandit's WebSock support is sufficient.
  socket "/socket", ChatF1Web.GraphqlSocket,
    websocket: [subprotocols: ["graphql-ws"]],
    longpoll: false

  # Standard Absinthe/Phoenix Channels socket — used by GraphiQL subscription
  # pane in dev.  Not used by the Apollo frontend (which uses /socket above).
  socket "/absinthe/socket", Absinthe.Phoenix.Socket,
    websocket: true,
    longpoll: false

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

  # CORS + x-viewer-token echo for the cross-origin React frontend (Phase 4).
  # Must sit before the Router so OPTIONS preflights short-circuit here.
  plug ChatF1Web.Plugs.CORS

  plug ChatF1Web.Router
end

defmodule ChatF1Web.GraphqlSocket do
  @moduledoc """
  graphql-ws WebSocket transport for Apollo GraphQLWsLink.

  This socket implements the standard `graphql-ws` sub-protocol so Apollo
  clients can use `GraphQLWsLink` directly — no `@absinthe/socket` shims
  needed.

  ## Viewer-token handshake

  The client sends a `connection_init` frame:

      {"type":"connection_init","payload":{"token":"<viewer_token>"}}

  `handle_init/2` verifies the token via `ChatF1.Accounts.verify_viewer_token/1`
  and injects `viewer_id` and `viewer_token` into the Absinthe context so
  subscription resolvers can perform authorization checks.

  A missing or invalid token is rejected with `{"type":"connection_error"}`,
  which closes the WebSocket.  This prevents anonymous subscription access
  while still allowing a fresh token to be minted on the HTTP side first.

  ## Why Absinthe.GraphqlWS over raw Phoenix Channels?

  `absinthe_graphql_ws 0.3.6` implements Phoenix.Socket.Transport directly —
  it does NOT require Cowboy or the Phoenix channel protocol.  Because Bandit
  exposes the WebSock behaviour, and Phoenix wraps it via `websock_adapter`,
  this works with our Phoenix 1.8 / Bandit stack out of the box.  The transport
  spike confirmed zero compatibility issues.
  """

  use Absinthe.GraphqlWS.Socket, schema: ChatF1Web.Schema

  alias ChatF1.Accounts

  @impl true
  @doc """
  Called on `connection_init`.  Validates the viewer token from the payload
  and injects identity into the Absinthe context.
  """
  def handle_init(%{"token" => token}, socket) when is_binary(token) do
    case Accounts.verify_viewer_token(token) do
      {:ok, viewer_id} ->
        socket =
          Absinthe.GraphqlWS.Util.assign_context(socket, %{
            viewer_id: viewer_id,
            viewer_token: token
          })

        {:ok, %{}, socket}

      {:error, _reason} ->
        {:error, %{message: "Unauthorized — invalid or expired viewer token"}, socket}
    end
  end

  def handle_init(_payload, socket) do
    {:error, %{message: "Unauthorized — viewer token required in connection_init payload"}, socket}
  end
end

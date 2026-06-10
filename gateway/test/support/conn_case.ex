defmodule ChatF1Web.ConnCase do
  @moduledoc """
  Test case for tests requiring an HTTP connection and optional DB access.
  Sets up the Ecto SQL sandbox and provides a pre-built `Plug.Conn`.
  """

  use ExUnit.CaseTemplate

  using do
    quote do
      @endpoint ChatF1Web.Endpoint

      import Plug.Conn
      import Phoenix.ConnTest
      import ChatF1Web.ConnCase

      alias ChatF1.Accounts
    end
  end

  setup tags do
    ChatF1.DataCase.setup_sandbox(tags)

    viewer_id = Ecto.UUID.generate()
    token = ChatF1.Accounts.mint_viewer_token(viewer_id)

    conn =
      Phoenix.ConnTest.build_conn()
      |> Plug.Conn.put_req_header("authorization", "Bearer #{token}")
      |> Plug.Conn.assign(:viewer_id, viewer_id)
      |> Plug.Conn.assign(:viewer_token, token)

    {:ok, conn: conn, viewer_id: viewer_id, viewer_token: token}
  end
end

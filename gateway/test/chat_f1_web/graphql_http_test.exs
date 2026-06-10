defmodule ChatF1Web.GraphQLHttpTest do
  @moduledoc """
  End-to-end tests through the real HTTP plug pipeline (`POST /graphql`).

  Resolver tests exercise the schema via `Absinthe.run/3` with a hand-built
  context; these tests exist to prove the *wiring* — that `Plugs.ViewerToken`
  actually delivers `viewer_id`/`viewer_token` into the Absinthe context, that
  GraphiQL rides the same pipeline, and that an operation consumes exactly one
  rate-limit token no matter how many fields it selects.
  """

  use ChatF1Web.ConnCase, async: false

  alias ChatF1.RateLimit.Server

  @drivers_query """
  query {
    drivers {
      code
      fullName
      constructor { name }
    }
  }
  """

  defp post_graphql(conn, query) do
    conn
    |> put_req_header("content-type", "application/json")
    |> post("/graphql", Jason.encode!(%{query: query}))
  end

  describe "POST /graphql through the full plug pipeline" do
    test "resolves a query with a minted viewer token", %{conn: conn} do
      response =
        conn
        |> post_graphql(@drivers_query)
        |> json_response(200)

      assert %{"data" => %{"drivers" => drivers}} = response
      refute Map.has_key?(response, "errors")
      assert is_list(drivers)
    end

    test "mints a viewer cookie for a first-time visitor with no token" do
      conn =
        Phoenix.ConnTest.build_conn()
        |> post_graphql(@drivers_query)

      assert %{"data" => _} = json_response(conn, 200)
      assert %{"_chat_f1_viewer" => %{value: token}} = conn.resp_cookies
      assert {:ok, _viewer_id} = ChatF1.Accounts.verify_viewer_token(token)
    end

    test "one operation consumes exactly one rate-limit token", %{conn: conn} do
      ["Bearer " <> token] = get_req_header(conn, "authorization")
      key = :crypto.hash(:sha256, token) |> Base.encode16(case: :lower)

      before = Server.status(key)
      _ = post_graphql(conn, @drivers_query) |> json_response(200)
      after_ = Server.status(key)

      assert before.remaining_minute - after_.remaining_minute == 1
    end

    test "validation errors come back normalized with an ErrorCode", %{conn: conn} do
      mutation = """
      mutation {
        startConversation { id }
      }
      """

      %{"data" => %{"startConversation" => %{"id" => conv_id}}} =
        conn |> post_graphql(mutation) |> json_response(200)

      send_message = """
      mutation {
        sendMessage(conversationId: "#{conv_id}", content: "") {
          assistantMessageId
        }
      }
      """

      response = conn |> post_graphql(send_message) |> json_response(200)

      assert [%{"extensions" => %{"code" => code}} | _] = response["errors"]
      assert code in ["VALIDATION", "BAD_USER_INPUT"]
    end
  end

  describe "GET /graphiql" do
    test "serves the playground through the same viewer pipeline" do
      conn =
        Phoenix.ConnTest.build_conn()
        |> put_req_header("accept", "text/html")
        |> get("/graphiql")

      assert conn.status == 200
      assert %{"_chat_f1_viewer" => _} = conn.resp_cookies
    end
  end
end

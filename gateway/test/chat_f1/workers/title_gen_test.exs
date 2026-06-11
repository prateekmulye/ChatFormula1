defmodule ChatF1.Workers.TitleGenTest do
  @moduledoc """
  Tests for the TitleGen Oban worker.

  Uses Bypass to mock the agent's /internal/chat endpoint, which AgentClient
  calls via HTTP.
  """

  # async: false — Application.put_env(:agent_url) is global state
  use ChatF1.DataCase, async: false
  use Oban.Testing, repo: ChatF1.Repo

  alias ChatF1.Accounts
  alias ChatF1.Conversations
  alias ChatF1.Conversations.Conversation
  alias ChatF1.Repo
  alias ChatF1.Workers.TitleGen

  setup do
    bypass = Bypass.open()
    Application.put_env(:chat_f1, :agent_url, "http://localhost:#{bypass.port}")
    Application.put_env(:chat_f1, :internal_api_token, "test-token")
    {:ok, bypass: bypass}
  end

  defp create_conversation_with_message do
    viewer_id = Accounts.new_viewer_id()
    {:ok, conv} = Conversations.create_conversation(viewer_id)
    {:ok, _} = Conversations.insert_message_pair(conv.id, "Who won Monaco 2024?")
    conv
  end

  # NDJSON response for a title generation prompt.
  defp title_ndjson(title) do
    ~s({"event":"token","text":"#{title}"}\n) <>
      ~s({"event":"complete","content":"#{title}","cached":false,"usage":null}\n)
  end

  test "perform/1 generates title and updates conversation", %{bypass: bypass} do
    conv = create_conversation_with_message()
    assert conv.title == nil

    Bypass.expect_once(bypass, "POST", "/internal/chat", fn conn ->
      conn
      |> Plug.Conn.put_resp_content_type("application/x-ndjson")
      |> Plug.Conn.send_resp(200, title_ndjson("Verstappen wins Monaco"))
    end)

    assert :ok = perform_job(TitleGen, %{"conversation_id" => conv.id})

    updated = Repo.get(Conversation, conv.id)
    assert updated.title == "Verstappen wins Monaco"
  end

  test "perform/1 degrades silently when agent returns error", %{bypass: bypass} do
    conv = create_conversation_with_message()

    Bypass.expect_once(bypass, "POST", "/internal/chat", fn conn ->
      Plug.Conn.send_resp(conn, 500, "error")
    end)

    # Must return :ok — missing title is not worth a retry storm.
    assert :ok = perform_job(TitleGen, %{"conversation_id" => conv.id})
  end

  test "perform/1 returns :ok for non-existent conversation_id" do
    assert :ok = perform_job(TitleGen, %{"conversation_id" => 0})
  end

  test "perform/1 is idempotent — skips if title already set", %{bypass: bypass} do
    viewer_id = Accounts.new_viewer_id()
    {:ok, conv} = Conversations.create_conversation(viewer_id)
    # Set title manually.
    {:ok, conv} = conv |> Conversation.changeset(%{title: "Existing Title"}) |> Repo.update()

    # Bypass should NOT be hit — the worker exits early.
    Bypass.expect(bypass, "POST", "/internal/chat", fn conn ->
      # If this is called, the test will fail because we're checking idempotency.
      flunk("Agent should not be called when title already exists")
      Plug.Conn.send_resp(conn, 200, "")
    end)

    assert :ok = perform_job(TitleGen, %{"conversation_id" => conv.id})
    # Bypass.pass ensures no pending expectations are violated.
    Bypass.pass(bypass)
  end
end

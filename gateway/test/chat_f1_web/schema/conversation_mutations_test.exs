defmodule ChatF1Web.Schema.ConversationMutationsTest do
  @moduledoc """
  GraphQL tests for conversation mutations and IDOR regression test.
  """

  use ChatF1.DataCase, async: true

  alias ChatF1.{Accounts, Conversations}
  alias ChatF1.Test.ConversationFixtures

  defp run_query(query, variables \\ %{}, viewer_id \\ nil, viewer_token \\ nil) do
    viewer_id = viewer_id || Accounts.new_viewer_id()
    viewer_token = viewer_token || Accounts.mint_viewer_token(viewer_id)

    Absinthe.run(query, ChatF1Web.Schema,
      context: %{viewer_id: viewer_id, viewer_token: viewer_token},
      variables: variables
    )
    |> case do
      {:ok, result} -> result
      other -> other
    end
  end

  describe "startConversation mutation" do
    test "creates a conversation for the viewer" do
      result = run_query("mutation { startConversation { id } }")
      assert Map.get(result, :errors, []) == []
      assert is_binary(result.data["startConversation"]["id"])
    end
  end

  describe "deleteConversation mutation" do
    test "deletes the viewer's own conversation" do
      {viewer_id, token} = ConversationFixtures.viewer_fixture()
      {:ok, conv} = Conversations.create_conversation(viewer_id)

      result =
        run_query(
          "mutation DeleteConv($id: ID!) { deleteConversation(id: $id) }",
          %{"id" => to_string(conv.id)},
          viewer_id,
          token
        )

      assert result.data["deleteConversation"] == true
      assert Conversations.get_conversation(to_string(conv.id), viewer_id) == nil
    end
  end

  describe "IDOR regression — conversation/conversations queries" do
    test "conversation query returns null for another viewer's conversation" do
      # Viewer A creates a conversation
      {viewer_a_id, _} = ConversationFixtures.viewer_fixture()
      {:ok, conv} = Conversations.create_conversation(viewer_a_id)

      # Viewer B tries to access it
      {viewer_b_id, viewer_b_token} = ConversationFixtures.viewer_fixture()

      result =
        run_query(
          "query GetConv($id: ID!) { conversation(id: $id) { id } }",
          %{"id" => to_string(conv.id)},
          viewer_b_id,
          viewer_b_token
        )

      # Must be null — not an error, just not found
      assert result.data["conversation"] == nil
      assert Map.get(result, :errors, []) == []
    end

    test "conversations query only returns the viewer's own conversations" do
      {v1_id, v1_token} = ConversationFixtures.viewer_fixture()
      {v2_id, v2_token} = ConversationFixtures.viewer_fixture()

      {:ok, _} = Conversations.create_conversation(v1_id)
      {:ok, _} = Conversations.create_conversation(v2_id)
      {:ok, _} = Conversations.create_conversation(v2_id)

      result_v1 = run_query("{ conversations { id } }", %{}, v1_id, v1_token)
      result_v2 = run_query("{ conversations { id } }", %{}, v2_id, v2_token)

      assert length(result_v1.data["conversations"]) == 1
      assert length(result_v2.data["conversations"]) == 2
    end
  end

  describe "rateLimitStatus query" do
    test "returns rate limit fields" do
      result =
        run_query(
          "{ rateLimitStatus { limitPerMinute remainingMinute limitPerHour remainingHour } }"
        )

      assert Map.get(result, :errors, []) == []
      status = result.data["rateLimitStatus"]
      assert is_integer(status["limitPerMinute"])
      assert is_integer(status["remainingMinute"])
    end
  end
end

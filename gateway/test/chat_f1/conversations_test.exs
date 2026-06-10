defmodule ChatF1.ConversationsTest do
  use ChatF1.DataCase, async: true

  alias ChatF1.{Accounts, Conversations}
  alias ChatF1.Test.ConversationFixtures

  describe "create_conversation/1" do
    test "creates a conversation for the viewer" do
      viewer_id = Accounts.new_viewer_id()
      assert {:ok, conv} = Conversations.create_conversation(viewer_id)
      assert conv.viewer_id == viewer_id
    end
  end

  describe "list_conversations/1" do
    test "returns only the viewer's own conversations" do
      {v1, _} = ConversationFixtures.viewer_fixture()
      {v2, _} = ConversationFixtures.viewer_fixture()

      ConversationFixtures.conversation_fixture(v1)
      ConversationFixtures.conversation_fixture(v1)
      ConversationFixtures.conversation_fixture(v2)

      v1_convs = Conversations.list_conversations(v1)
      v2_convs = Conversations.list_conversations(v2)

      assert length(v1_convs) == 2
      assert length(v2_convs) == 1
    end
  end

  describe "get_conversation/2 — IDOR regression" do
    test "returns nil when viewer_id does not match — the v1 IDOR is dead" do
      {owner_id, _} = ConversationFixtures.viewer_fixture()
      {attacker_id, _} = ConversationFixtures.viewer_fixture()

      {:ok, conv} = Conversations.create_conversation(owner_id)

      # Attacker knows the conversation ID but has a different viewer token.
      result = Conversations.get_conversation(to_string(conv.id), attacker_id)
      assert result == nil
    end

    test "returns the conversation for the correct owner" do
      {owner_id, _} = ConversationFixtures.viewer_fixture()
      {:ok, conv} = Conversations.create_conversation(owner_id)

      found = Conversations.get_conversation(to_string(conv.id), owner_id)
      assert found.id == conv.id
    end
  end

  describe "insert_message_pair/2" do
    test "inserts user and assistant messages atomically" do
      {viewer_id, _} = ConversationFixtures.viewer_fixture()
      {:ok, conv} = Conversations.create_conversation(viewer_id)

      assert {:ok, %{user_message: user_msg, assistant_message: asst_msg}} =
               Conversations.insert_message_pair(conv.id, "Tell me about Verstappen")

      assert user_msg.role == :user
      assert user_msg.content == "Tell me about Verstappen"
      assert user_msg.status == :complete

      assert asst_msg.role == :assistant
      assert asst_msg.status == :pending
      assert asst_msg.content == ""
    end

    test "rejects content exceeding 2000 characters" do
      {viewer_id, _} = ConversationFixtures.viewer_fixture()
      {:ok, conv} = Conversations.create_conversation(viewer_id)
      # Use alternating chars so repetition guard doesn't fire alongside length guard.
      long = String.duplicate("ab", 1001)

      assert {:error, :user_message, changeset, _} =
               Conversations.insert_message_pair(conv.id, long)

      errors = errors_on(changeset)
      assert "should be at most 2000 character(s)" in errors.content
    end

    test "rejects content with excessive character repetition" do
      {viewer_id, _} = ConversationFixtures.viewer_fixture()
      {:ok, conv} = Conversations.create_conversation(viewer_id)
      repeated = String.duplicate("a", 30)

      assert {:error, :user_message, changeset, _} =
               Conversations.insert_message_pair(conv.id, repeated)

      assert %{content: [msg]} = errors_on(changeset)
      assert msg =~ "excessive"
    end
  end

  describe "delete_conversation/2" do
    test "deletes the conversation for the owner" do
      {viewer_id, _} = ConversationFixtures.viewer_fixture()
      {:ok, conv} = Conversations.create_conversation(viewer_id)

      assert {:ok, _} = Conversations.delete_conversation(to_string(conv.id), viewer_id)
      assert Conversations.get_conversation(to_string(conv.id), viewer_id) == nil
    end

    test "returns not_found for another viewer's conversation" do
      {owner_id, _} = ConversationFixtures.viewer_fixture()
      {attacker_id, _} = ConversationFixtures.viewer_fixture()
      {:ok, conv} = Conversations.create_conversation(owner_id)

      assert {:error, :not_found} =
               Conversations.delete_conversation(to_string(conv.id), attacker_id)
    end
  end
end

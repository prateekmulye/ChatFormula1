defmodule ChatF1.Test.ConversationFixtures do
  @moduledoc "Factory helpers for conversation test data."

  alias ChatF1.{Accounts, Conversations}

  def viewer_fixture do
    id = Accounts.new_viewer_id()
    token = Accounts.mint_viewer_token(id)
    {id, token}
  end

  def conversation_fixture(viewer_id \\ nil) do
    viewer_id = viewer_id || Accounts.new_viewer_id()
    {:ok, conversation} = Conversations.create_conversation(viewer_id)
    conversation
  end
end

"""Tests for the conversation memory manager."""

import pytest
from langchain_core.messages import SystemMessage

from src.agent.memory import ConversationMemoryManager
from src.agent.state import ConversationContext


@pytest.fixture
def memory_manager(test_settings):
    """Fixture to create a ConversationMemoryManager instance."""
    return ConversationMemoryManager(config=test_settings)


class TestGetOrCreateSession:
    """Tests for get_or_create_session method."""

    def test_get_or_create_session_exists(self, memory_manager):
        """Test returning an existing session."""
        session_id = "test_session_exists"

        # Create session initially
        initial_session = memory_manager.create_session(session_id)

        # Retrieve it
        retrieved_session = memory_manager.get_or_create_session(session_id)

        # Verify it's exactly the same object
        assert retrieved_session is initial_session
        assert retrieved_session.session_id == session_id

    def test_get_or_create_session_does_not_exist(self, memory_manager):
        """Test creating a new session when it does not exist."""
        session_id = "test_session_new"

        # Ensure it doesn't exist
        assert memory_manager.get_session(session_id) is None

        # Get or create it
        new_session = memory_manager.get_or_create_session(session_id)

        # Verify it was created properly
        assert isinstance(new_session, ConversationContext)
        assert new_session.session_id == session_id
        assert len(new_session.messages) == 0

        # Verify it's now stored
        assert memory_manager.get_session(session_id) is new_session

    def test_get_or_create_session_does_not_exist_with_system_message(
        self, memory_manager
    ):
        """Test creating a new session with a system message."""
        session_id = "test_session_new_with_sys_msg"
        sys_msg = SystemMessage(content="You are a helpful assistant.")

        # Get or create it
        new_session = memory_manager.get_or_create_session(
            session_id=session_id, system_message=sys_msg
        )

        # Verify it was created and has the system message
        assert isinstance(new_session, ConversationContext)
        assert new_session.session_id == session_id
        assert len(new_session.messages) == 1
        assert new_session.messages[0] is sys_msg

        # Verify it's stored
        assert memory_manager.get_session(session_id) is new_session

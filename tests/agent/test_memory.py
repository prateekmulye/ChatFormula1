"""Tests for the memory manager."""


from langgraph.checkpoint.memory import MemorySaver

from src.agent.memory import ConversationMemoryManager, create_memory_manager
from src.config.settings import Settings


def test_create_memory_manager_default_checkpointer(test_settings: Settings) -> None:
    """Test create_memory_manager factory function with default checkpointer."""
    manager = create_memory_manager(test_settings)

    assert isinstance(manager, ConversationMemoryManager)
    assert manager.config == test_settings
    assert isinstance(manager.checkpointer, MemorySaver)


def test_create_memory_manager_custom_checkpointer(test_settings: Settings) -> None:
    """Test create_memory_manager factory function with custom checkpointer."""
    custom_checkpointer = MemorySaver()
    manager = create_memory_manager(test_settings, checkpointer=custom_checkpointer)

    assert isinstance(manager, ConversationMemoryManager)
    assert manager.config == test_settings
    assert manager.checkpointer is custom_checkpointer

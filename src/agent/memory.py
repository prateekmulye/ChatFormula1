"""Conversation context management with LangGraph memory.

This module provides conversation memory management using LangGraph's
MemorySaver for persistence, sliding window for history management,
and context summarization for long conversations.
"""

import json
from datetime import datetime
from typing import Any, Optional

import structlog
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver

from src.config.settings import Settings

from .state import AgentState, ConversationContext

logger = structlog.get_logger(__name__)


class ConversationMemoryManager:
    """Manages conversation memory with checkpointing and summarization.

    This class provides:
    - MemorySaver integration for conversation persistence
    - Sliding window for conversation history management
    - Context summarization for long conversations
    - Session state persistence with checkpointing
    - Context clearing functionality

    Attributes:
        config: Application settings
        checkpointer: MemorySaver instance for persistence
        llm: ChatOpenAI instance for summarization
        max_history: Maximum conversation history to maintain
    """

    def __init__(
        self,
        config: Settings,
        checkpointer: Optional[MemorySaver] = None,
    ) -> None:
        """Initialize conversation memory manager.

        Args:
            config: Application settings
            checkpointer: Optional MemorySaver instance (creates new if None)
        """
        self.config = config
        self.checkpointer = checkpointer or MemorySaver()
        self.max_history = config.max_conversation_history

        # Initialize LLM for summarization
        self.llm = ChatOpenAI(
            api_key=config.openai_api_key,
            model=config.openai_model,
            temperature=0.3,  # Lower temperature for consistent summaries
        )

        # In-memory session cache
        self._sessions: dict[str, ConversationContext] = {}

        logger.info(
            "conversation_memory_manager_initialized",
            max_history=self.max_history,
        )

    def create_session(
        self,
        session_id: str,
        system_message: Optional[BaseMessage] = None,
    ) -> ConversationContext:
        """Create a new conversation session.

        Args:
            session_id: Unique session identifier
            system_message: Optional system message to include

        Returns:
            New ConversationContext
        """
        messages = [system_message] if system_message else []

        context = ConversationContext(
            session_id=session_id,
            messages=messages,
            max_history=self.max_history,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        self._sessions[session_id] = context

        logger.info(
            "session_created",
            session_id=session_id,
            has_system_message=system_message is not None,
        )

        return context

    def get_session(self, session_id: str) -> Optional[ConversationContext]:
        """Get existing conversation session.

        Args:
            session_id: Session identifier

        Returns:
            ConversationContext if exists, None otherwise
        """
        return self._sessions.get(session_id)

    def get_or_create_session(
        self,
        session_id: str,
        system_message: Optional[BaseMessage] = None,
    ) -> ConversationContext:
        """Get existing session or create new one.

        Args:
            session_id: Session identifier
            system_message: Optional system message for new sessions

        Returns:
            ConversationContext
        """
        session = self.get_session(session_id)
        if session is None:
            session = self.create_session(session_id, system_message)
        return session

    def add_message(
        self,
        session_id: str,
        message: BaseMessage,
    ) -> ConversationContext:
        """Add a message to conversation history with sliding window.

        Implements sliding window to maintain max_history limit.

        Args:
            session_id: Session identifier
            message: Message to add

        Returns:
            Updated ConversationContext
        """
        session = self.get_or_create_session(session_id)
        session.add_message(message)

        logger.debug(
            "message_added",
            session_id=session_id,
            message_type=message.type,
            total_messages=len(session.messages),
        )

        return session

    def add_exchange(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
    ) -> ConversationContext:
        """Add a complete user-assistant exchange.

        Args:
            session_id: Session identifier
            user_message: User's message content
            assistant_message: Assistant's response content

        Returns:
            Updated ConversationContext
        """
        session = self.get_or_create_session(session_id)

        session.add_message(HumanMessage(content=user_message))
        session.add_message(AIMessage(content=assistant_message))

        logger.info(
            "exchange_added",
            session_id=session_id,
            total_messages=len(session.messages),
        )

        return session

    def get_recent_messages(
        self,
        session_id: str,
        count: int = 5,
    ) -> list[BaseMessage]:
        """Get recent messages from conversation history.

        Args:
            session_id: Session identifier
            count: Number of message pairs to retrieve

        Returns:
            List of recent messages
        """
        session = self.get_session(session_id)
        if session is None:
            return []

        return session.get_recent_messages(count)

    async def summarize_conversation(
        self,
        session_id: str,
    ) -> Optional[str]:
        """Summarize conversation history for long conversations.

        Uses LLM to create a concise summary of the conversation so far,
        which can be used to maintain context while reducing token usage.

        Args:
            session_id: Session identifier

        Returns:
            Summary string or None if session doesn't exist
        """
        session = self.get_session(session_id)
        if session is None:
            return None

        # Only summarize if we have enough messages
        if len(session.messages) < self.max_history:
            return None

        logger.info(
            "summarizing_conversation",
            session_id=session_id,
            message_count=len(session.messages),
        )

        # Build conversation text
        conversation_text = []
        for msg in session.messages:
            if msg.type == "system":
                continue
            role = "User" if msg.type == "human" else "Assistant"
            conversation_text.append(f"{role}: {msg.content}")

        conversation_str = "\n\n".join(conversation_text)

        # Create summarization prompt
        summary_prompt = f"""Summarize the following F1 conversation concisely, capturing:
1. Main topics discussed
2. Key information provided
3. User's apparent interests or questions
4. Any ongoing context that should be remembered

Keep the summary under 200 words.

Conversation:
{conversation_str}

Summary:"""

        try:
            response = await self.llm.ainvoke([HumanMessage(content=summary_prompt)])
            summary = response.content

            logger.info(
                "conversation_summarized",
                session_id=session_id,
                summary_length=len(summary),
            )

            # Store summary in session metadata
            session.metadata["summary"] = summary
            session.metadata["summarized_at"] = datetime.now().isoformat()

            return summary

        except Exception as e:
            logger.error(
                "summarization_failed",
                session_id=session_id,
                error=str(e),
            )
            return None

    async def apply_sliding_window_with_summary(
        self,
        session_id: str,
    ) -> ConversationContext:
        """Apply sliding window with summarization for long conversations.

        When conversation exceeds max_history, this method:
        1. Summarizes older messages
        2. Replaces them with a summary message
        3. Keeps recent messages intact

        Args:
            session_id: Session identifier

        Returns:
            Updated ConversationContext
        """
        session = self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        # Check if we need to apply sliding window
        non_system_messages = [m for m in session.messages if m.type != "system"]
        if len(non_system_messages) <= self.max_history * 2:
            return session

        logger.info(
            "applying_sliding_window_with_summary",
            session_id=session_id,
            current_messages=len(non_system_messages),
        )

        # Summarize older messages
        summary = await self.summarize_conversation(session_id)

        # Keep system messages
        system_messages = [m for m in session.messages if m.type == "system"]

        # Keep recent messages
        recent_messages = non_system_messages[-(self.max_history * 2) :]

        # Create summary message if we have a summary
        new_messages = system_messages.copy()
        if summary:
            summary_message = SystemMessage(
                content=f"[Conversation Summary]\n{summary}"
            )
            new_messages.append(summary_message)

        new_messages.extend(recent_messages)

        # Update session
        session.messages = new_messages
        session.updated_at = datetime.now()

        logger.info(
            "sliding_window_applied",
            session_id=session_id,
            new_message_count=len(new_messages),
        )

        return session

    def clear_session(self, session_id: str) -> bool:
        """Clear conversation history for a session.

        Preserves system messages and session metadata.

        Args:
            session_id: Session identifier

        Returns:
            True if session was cleared, False if not found
        """
        session = self.get_session(session_id)
        if session is None:
            return False

        session.clear()

        logger.info(
            "session_cleared",
            session_id=session_id,
        )

        return True

    def delete_session(self, session_id: str) -> bool:
        """Delete a session completely.

        Args:
            session_id: Session identifier

        Returns:
            True if session was deleted, False if not found
        """
        if session_id in self._sessions:
            del self._sessions[session_id]

            logger.info(
                "session_deleted",
                session_id=session_id,
            )

            return True

        return False

    def save_checkpoint(
        self,
        session_id: str,
        state: AgentState,
    ) -> None:
        """Save conversation state checkpoint.

        Uses MemorySaver to persist conversation state for recovery.

        Args:
            session_id: Session identifier
            state: Current agent state to checkpoint
        """
        try:
            # Convert state to dict for serialization
            checkpoint_data = {
                "session_id": session_id,
                "messages": [
                    {
                        "type": msg.type,
                        "content": msg.content,
                    }
                    for msg in state.messages
                ],
                "query": state.query,
                "intent": state.intent,
                "entities": state.entities,
                "metadata": state.metadata,
                "timestamp": state.timestamp.isoformat(),
            }

            # Save using checkpointer
            config = {"configurable": {"thread_id": session_id}}
            self.checkpointer.put(
                config,
                checkpoint_data,
                {},  # metadata
            )

            logger.debug(
                "checkpoint_saved",
                session_id=session_id,
            )

        except Exception as e:
            logger.error(
                "checkpoint_save_failed",
                session_id=session_id,
                error=str(e),
            )

    def load_checkpoint(
        self,
        session_id: str,
    ) -> Optional[dict[str, Any]]:
        """Load conversation state from checkpoint.

        Args:
            session_id: Session identifier

        Returns:
            Checkpoint data or None if not found
        """
        try:
            config = {"configurable": {"thread_id": session_id}}
            checkpoint = self.checkpointer.get(config)

            if checkpoint:
                logger.debug(
                    "checkpoint_loaded",
                    session_id=session_id,
                )
                return checkpoint

            return None

        except Exception as e:
            logger.error(
                "checkpoint_load_failed",
                session_id=session_id,
                error=str(e),
            )
            return None

    def get_session_stats(self, session_id: str) -> Optional[dict[str, Any]]:
        """Get statistics about a conversation session.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary with session statistics or None if not found
        """
        session = self.get_session(session_id)
        if session is None:
            return None

        non_system_messages = [m for m in session.messages if m.type != "system"]
        user_messages = [m for m in non_system_messages if m.type == "human"]
        assistant_messages = [m for m in non_system_messages if m.type == "ai"]

        return {
            "session_id": session_id,
            "total_messages": len(session.messages),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "has_summary": "summary" in session.metadata,
            "metadata": session.metadata,
        }

    def list_sessions(self) -> list[str]:
        """List all active session IDs.

        Returns:
            List of session IDs
        """
        return list(self._sessions.keys())

    def export_session(self, session_id: str) -> Optional[dict[str, Any]]:
        """Export session data for backup or analysis.

        Args:
            session_id: Session identifier

        Returns:
            Serializable session data or None if not found
        """
        session = self.get_session(session_id)
        if session is None:
            return None

        return {
            "session_id": session.session_id,
            "messages": [
                {
                    "type": msg.type,
                    "content": msg.content,
                }
                for msg in session.messages
            ],
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "metadata": session.metadata,
        }

    def import_session(self, session_data: dict[str, Any]) -> ConversationContext:
        """Import session data from backup.

        Args:
            session_data: Serialized session data

        Returns:
            Restored ConversationContext
        """
        session_id = session_data["session_id"]

        # Reconstruct messages
        messages = []
        for msg_data in session_data["messages"]:
            msg_type = msg_data["type"]
            content = msg_data["content"]

            if msg_type == "system":
                messages.append(SystemMessage(content=content))
            elif msg_type == "human":
                messages.append(HumanMessage(content=content))
            elif msg_type == "ai":
                messages.append(AIMessage(content=content))

        # Create session
        session = ConversationContext(
            session_id=session_id,
            messages=messages,
            max_history=self.max_history,
            created_at=datetime.fromisoformat(session_data["created_at"]),
            updated_at=datetime.fromisoformat(session_data["updated_at"]),
            metadata=session_data.get("metadata", {}),
        )

        self._sessions[session_id] = session

        logger.info(
            "session_imported",
            session_id=session_id,
            message_count=len(messages),
        )

        return session


def create_memory_manager(
    config: Settings,
    checkpointer: Optional[MemorySaver] = None,
) -> ConversationMemoryManager:
    """Factory function to create a ConversationMemoryManager.

    Args:
        config: Application settings
        checkpointer: Optional MemorySaver instance

    Returns:
        Configured ConversationMemoryManager
    """
    return ConversationMemoryManager(config=config, checkpointer=checkpointer)

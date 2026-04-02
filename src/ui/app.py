"""Streamlit UI for ChatFormula1 chatbot.

This module implements the main Streamlit application with:
- Session state management
- Chat interface with streaming responses
- Source citations and metadata display
- Error handling and user feedback
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Optional

import streamlit as st
import structlog
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.agent.graph import F1AgentGraph
from src.agent.state import create_initial_state
from src.config.settings import get_settings
from src.prompts.system_prompts import F1_EXPERT_SYSTEM_PROMPT
from src.search.tavily_client import TavilyClient
from src.ui.components import (
    apply_f1_theme,
    render_about_modal,
    render_error_message,
    render_input_validation_error,
    render_message,
    render_settings_panel,
    render_welcome_screen,
)
from src.vector_store.manager import VectorStoreManager

logger = structlog.get_logger(__name__)


# Page configuration
st.set_page_config(
    page_title="ChatFormula1",
    page_icon="🏎️",
    layout="wide",
    menu_items={
        "Get Help": "https://github.com/prateekmulye/chatformula1",
        "Report a bug": "https://github.com/prateekmulye/chatformula1/issues",
        "About": "# ChatFormula1\nYour AI-powered Formula 1 expert assistant",
    },
)


def initialize_session_state() -> None:
    """Initialize Streamlit session state with default values."""
    # Session ID for conversation tracking
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
        logger.info("session_created", session_id=st.session_state.session_id)

    # Message history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Agent state
    if "agent_state" not in st.session_state:
        st.session_state.agent_state = None

    # Settings
    if "settings" not in st.session_state:
        try:
            st.session_state.settings = get_settings()
        except Exception as e:
            st.error(f"⚠️ Configuration Error: {str(e)}")
            st.stop()

    # Agent components (lazy initialization)
    if "agent_graph" not in st.session_state:
        st.session_state.agent_graph = None

    if "vector_store" not in st.session_state:
        st.session_state.vector_store = None

    if "tavily_client" not in st.session_state:
        st.session_state.tavily_client = None

    # UI state
    if "show_settings" not in st.session_state:
        st.session_state.show_settings = False

    if "show_about" not in st.session_state:
        st.session_state.show_about = False

    if "theme" not in st.session_state:
        st.session_state.theme = "dark"

    if "prompt_executed" not in st.session_state:
        st.session_state.prompt_executed = False

    # Feedback state
    if "feedback" not in st.session_state:
        st.session_state.feedback = {}

    # Error state
    if "last_error" not in st.session_state:
        st.session_state.last_error = None


def initialize_agent() -> Optional[F1AgentGraph]:
    """Initialize the agent graph and dependencies.

    Returns:
        Initialized F1AgentGraph or None if initialization fails
    """
    if st.session_state.agent_graph is not None:
        return st.session_state.agent_graph

    try:
        with st.spinner("🔧 Initializing ChatFormula1 agent..."):
            settings = st.session_state.settings

            # Initialize vector store
            if st.session_state.vector_store is None:
                st.session_state.vector_store = VectorStoreManager(settings)
                # Initialize vector store asynchronously
                asyncio.run(st.session_state.vector_store.initialize())
                logger.info("vector_store_initialized")

            # Initialize Tavily client
            if st.session_state.tavily_client is None:
                st.session_state.tavily_client = TavilyClient(settings)
                logger.info("tavily_client_initialized")

            # Initialize agent graph
            agent_graph = F1AgentGraph(
                config=settings,
                vector_store=st.session_state.vector_store,
                tavily_client=st.session_state.tavily_client,
            )

            # Compile graph with memory
            agent_graph.compile()

            st.session_state.agent_graph = agent_graph
            logger.info("agent_graph_initialized")

            return agent_graph

    except Exception as e:
        error_msg = f"Failed to initialize agent: {str(e)}"
        logger.error("agent_initialization_failed", error=str(e), exc_info=True)
        st.session_state.last_error = error_msg
        return None


def render_sidebar() -> None:
    """Render the sidebar with settings and controls."""
    with st.sidebar:
        st.title("⚙️ Settings")

        # Theme toggle
        st.subheader("🎨 Appearance")
        theme = st.radio(
            "Theme",
            options=["Dark", "Light"],
            index=0 if st.session_state.theme == "dark" else 1,
            horizontal=True,
            label_visibility="collapsed",
        )
        st.session_state.theme = theme.lower()

        st.divider()

        # Model settings
        st.subheader("🤖 Model Settings")

        # Temperature control
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=2.0,
            value=st.session_state.settings.openai_temperature,
            step=0.1,
            help="Higher values make output more creative, lower values more focused",
        )

        if temperature != st.session_state.settings.openai_temperature:
            st.session_state.settings.openai_temperature = temperature
            # Reset agent to apply new settings
            st.session_state.agent_graph = None

        # Max history
        max_history = st.slider(
            "Conversation History",
            min_value=5,
            max_value=20,
            value=st.session_state.settings.max_conversation_history,
            step=1,
            help="Number of previous messages to include as context",
        )

        if max_history != st.session_state.settings.max_conversation_history:
            st.session_state.settings.max_conversation_history = max_history

        st.divider()

        # Conversation management
        st.subheader("💬 Conversation")

        # Message count
        msg_count = len(st.session_state.messages)
        st.metric("Messages", msg_count)

        # Clear conversation button
        if st.button("🗑️ Clear Conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.agent_state = None
            st.session_state.feedback = {}
            logger.info("conversation_cleared", session_id=st.session_state.session_id)
            st.rerun()

        # New session button
        if st.button("🆕 New Session", use_container_width=True):
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.session_state.agent_state = None
            st.session_state.feedback = {}
            logger.info("new_session_created", session_id=st.session_state.session_id)
            st.rerun()

        st.divider()

        # System info
        st.subheader("ℹ️ System Info")

        # Agent status
        agent_status = (
            "✅ Ready" if st.session_state.agent_graph else "⚠️ Not Initialized"
        )
        st.text(f"Agent: {agent_status}")

        # Session ID (truncated)
        session_id_short = st.session_state.session_id[:8]
        st.text(f"Session: {session_id_short}...")

        # Environment
        env = st.session_state.settings.environment
        st.text(f"Environment: {env}")

        st.divider()

        # Help section
        with st.expander("❓ Help & Tips"):
            st.markdown(
                """
            **What can I ask?**
            - Current F1 standings and results
            - Historical statistics and records
            - Race predictions and analysis
            - Technical regulations and rules
            - Driver and team information
            
            **Tips:**
            - Be specific with your questions
            - Mention years, drivers, or races for better context
            - Ask follow-up questions naturally
            - Use the feedback buttons to help improve responses
            """
            )

        # About section
        with st.expander("ℹ️ About"):
            st.markdown(
                """
            **ChatFormula1** is an AI-powered Formula 1 expert assistant
            that combines:
            - Real-time F1 data and news
            - Historical F1 knowledge base
            - Advanced language models
            - RAG (Retrieval-Augmented Generation)
            
            Built with LangChain, LangGraph, Pinecone, and Streamlit.
            
            ---
            
            **Created by:** Prateek Mulye
            
            **Connect:**
            - 🔗 LinkedIn: [linkedin.com/in/prateekmulye](https://www.linkedin.com/in/prateekmulye/)
            - 💻 GitHub: [github.com/prateekmulye](https://github.com/prateekmulye)
            """
            )


def render_header() -> None:
    """Render the enhanced header with About and Settings buttons.

    Accessibility features:
    - ARIA labels on icon-only buttons for screen readers
    - Descriptive help text for keyboard users
    - Semantic HTML structure with proper heading hierarchy
    - High contrast colors meeting WCAG 2.1 Level AA standards

    Requirements: 4.6, 5.5
    """
    # Three-column layout for settings button, title, and about button
    col1, col2, col3 = st.columns([1, 6, 1])

    with col1:
        # Settings button (left) with ARIA label for accessibility
        if st.button(
            "⚙️",
            key="settings_btn",
            help="Open Settings - Configure temperature, conversation history, and system options",
            use_container_width=False,
        ):
            st.session_state.show_settings = not st.session_state.show_settings
            st.rerun()

    with col2:
        # Centered title and tagline using semantic HTML with proper heading hierarchy
        # ARIA role="banner" indicates this is the main header
        st.markdown(
            """
            <div role="banner" style='text-align: center;'>
                <h1 style='margin-bottom: 0;'>🏎️ ChatFormula1</h1>
                <p style='color: #888; margin-top: 0;' role="doc-subtitle">Your AI-powered Formula 1 expert assistant</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        # About button (right) with ARIA label for accessibility
        if st.button(
            "ℹ️",
            key="about_btn",
            help="About ChatFormula1 - Learn about the project, features, and creator",
            use_container_width=False,
        ):
            st.session_state.show_about = not st.session_state.show_about
            st.rerun()


def render_chat_interface(agent: Optional[F1AgentGraph]) -> None:
    """Render the main chat interface with message history and input.

    This function implements the ChatGPT/Anthropic UX pattern where:
    - The welcome screen is shown when no messages exist
    - The chat input (search bar) is ALWAYS visible, even on the welcome screen
    - Recommendation prompts disappear once the user sends their first message
    - The UI stays clean and focused on the conversation

    Args:
        agent: Initialized F1AgentGraph or None

    Requirements: 8.6, 3.5, 4.6, 5.5
    """
    # Show welcome screen if no messages (Requirements: 3.4, 8.6)
    # Welcome screen includes hero, description, and recommendation prompts
    # The persistent search bar (chat input) is rendered below, always visible
    if not st.session_state.messages:
        render_welcome_screen()
        # Chat input will be rendered below (persistent search bar pattern)

    # Display message history (only if messages exist)
    if st.session_state.messages:
        for i, msg in enumerate(st.session_state.messages):
            message_id = f"msg_{st.session_state.session_id}_{i}"
            render_message(
                role=msg["role"],
                content=msg["content"],
                metadata=msg.get("metadata"),
                message_id=message_id if msg["role"] == "assistant" else None,
            )

    # Check if a prompt was just executed (from recommendation button)
    if st.session_state.get("prompt_executed", False):
        # Get the last user message (the one just added by execute_prompt)
        last_message = st.session_state.messages[-1]
        prompt = last_message["content"]

        # Clear the flag
        st.session_state.prompt_executed = False

        # Generate response
        with st.chat_message("assistant"):
            response_placeholder = st.empty()

            try:
                # Show typing indicator
                with st.spinner("Thinking..."):
                    # Process query through agent
                    response_text, metadata = asyncio.run(process_query(agent, prompt))

                # Display response with markdown
                response_placeholder.markdown(response_text)

                # Add assistant message to history
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": response_text,
                        "metadata": metadata,
                        "timestamp": datetime.now(),
                    }
                )

                logger.info(
                    "message_exchange_completed",
                    session_id=st.session_state.session_id,
                    user_query_length=len(prompt),
                    response_length=len(response_text),
                )

                # Rerun to show feedback buttons
                st.rerun()

            except Exception as e:
                error_msg = str(e)
                logger.error(
                    "message_processing_failed",
                    error=error_msg,
                    session_id=st.session_state.session_id,
                )

                # Show error to user
                render_error_message(error_msg, show_details=True)

                # Add error message to history
                error_response = (
                    "I apologize, but I encountered an error processing your request. "
                    "Please try rephrasing your question or try again later."
                )
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": error_response,
                        "metadata": {"error": error_msg},
                        "timestamp": datetime.now(),
                    }
                )

    # Chat input
    if prompt := st.chat_input(
        "Ask me anything about Formula 1...",
        key="chat_input",
        disabled=agent is None,
    ):
        # Validate input
        if not prompt.strip():
            render_input_validation_error("empty")
            return

        if len(prompt) > 500:
            render_input_validation_error("too_long")
            return

        # Add user message to history
        st.session_state.messages.append(
            {
                "role": "user",
                "content": prompt,
                "timestamp": datetime.now(),
            }
        )

        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            response_placeholder = st.empty()

            try:
                # Show typing indicator
                with st.spinner("Thinking..."):
                    # Process query through agent
                    response_text, metadata = asyncio.run(process_query(agent, prompt))

                # Display response with markdown
                response_placeholder.markdown(response_text)

                # Add assistant message to history
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": response_text,
                        "metadata": metadata,
                        "timestamp": datetime.now(),
                    }
                )

                logger.info(
                    "message_exchange_completed",
                    session_id=st.session_state.session_id,
                    user_query_length=len(prompt),
                    response_length=len(response_text),
                )

                # Rerun to show feedback buttons
                st.rerun()

            except Exception as e:
                error_msg = str(e)
                logger.error(
                    "message_processing_failed",
                    error=error_msg,
                    session_id=st.session_state.session_id,
                )

                # Show error to user
                render_error_message(error_msg, show_details=True)

                # Add error message to history
                error_response = (
                    "I apologize, but I encountered an error processing your request. "
                    "Please try rephrasing your question or try again later."
                )
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": error_response,
                        "metadata": {"error": error_msg},
                        "timestamp": datetime.now(),
                    }
                )


async def process_query(
    agent: F1AgentGraph,
    query: str,
) -> tuple[str, dict[str, Any]]:
    """Process user query through the agent graph.

    Args:
        agent: Initialized F1AgentGraph
        query: User query string

    Returns:
        Tuple of (response_text, metadata)
    """
    # Create or update agent state
    if st.session_state.agent_state is None:
        # Create initial state
        system_msg = SystemMessage(content=F1_EXPERT_SYSTEM_PROMPT)
        st.session_state.agent_state = create_initial_state(
            session_id=st.session_state.session_id,
            system_message=system_msg,
        )

    # Get current state and add user message
    current_state = st.session_state.agent_state

    # Create input state with query and existing messages
    input_state = {
        "query": query,
        "messages": list(current_state.messages) + [HumanMessage(content=query)],
        "session_id": st.session_state.session_id,
        "timestamp": datetime.now(),
        "metadata": current_state.metadata,
    }

    # Invoke agent graph with thread-based memory
    config = {"configurable": {"thread_id": st.session_state.session_id}}

    try:
        # Run agent graph
        result = await agent.compiled_graph.ainvoke(
            input_state,
            config=config,
        )

        # Extract response and metadata
        response_text = result.get("response", "")

        if not response_text:
            logger.warning("empty_response_from_agent", query=query)
            response_text = "I apologize, but I couldn't generate a response. Please try rephrasing your question."

        # Build metadata for UI
        metadata = {
            "intent": result.get("intent"),
            "sources": [],
            "warnings": [],
        }

        # Add vector store sources
        retrieved_docs = result.get("retrieved_docs", [])
        for doc in retrieved_docs[:3]:  # Top 3
            metadata["sources"].append(
                {
                    "type": "historical",
                    "content": doc.get("content", ""),
                    "metadata": doc.get("metadata", {}),
                    "score": 0.8,
                }
            )

        # Add search results
        search_results = result.get("search_results", [])
        for res in search_results[:3]:  # Top 3
            metadata["sources"].append(
                {
                    "type": "current",
                    "title": res.get("title", ""),
                    "url": res.get("url", ""),
                    "content": res.get("content", ""),
                    "score": res.get("score", 0.7),
                }
            )

        # Add warnings if any
        result_metadata = result.get("metadata", {})
        if result_metadata.get("tavily_fallback"):
            metadata["warnings"].append(
                "⚠️ Real-time search temporarily unavailable. Using cached knowledge."
            )

        if result_metadata.get("vector_search_error"):
            metadata["warnings"].append(
                "⚠️ Historical context may be limited due to a temporary issue."
            )

        # Update agent state with result
        # Convert result dict back to AgentState for next iteration
        from src.agent.state import AgentState

        st.session_state.agent_state = AgentState(**result)

        logger.info(
            "query_processed_successfully",
            query_length=len(query),
            response_length=len(response_text),
            sources_count=len(metadata["sources"]),
            warnings_count=len(metadata["warnings"]),
        )

        return response_text, metadata

    except Exception as e:
        logger.error("agent_invocation_failed", error=str(e), exc_info=True)
        raise


def main() -> None:
    """Main application entry point."""
    # Initialize session state
    initialize_session_state()

    # Track session start time
    if "session_start" not in st.session_state:
        st.session_state.session_start = datetime.now()

    # Apply F1 theme CSS with centered layout
    apply_f1_theme()

    # Create centered layout with three columns [1, 6, 1]
    col_left, col_center, col_right = st.columns([1, 6, 1])

    with col_center:
        # Render header
        render_header()

        # Render settings panel (collapsible, positioned below header)
        render_settings_panel()

        # Render about modal if triggered
        render_about_modal()

        # Initialize agent (lazy)
        agent = initialize_agent()

        # Show error if agent failed to initialize
        if st.session_state.last_error:
            st.error(f"⚠️ {st.session_state.last_error}")
            st.info("Please check your configuration and try again.")
            return

        # Render chat interface
        render_chat_interface(agent)


if __name__ == "__main__":
    main()

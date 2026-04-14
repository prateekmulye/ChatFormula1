"""Integration tests for complete system wiring.

Tests the integration of UI, agent, tools, and caching.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage

from src.agent.graph import F1AgentGraph
from src.agent.state import create_initial_state
from src.config.settings import Settings
from src.search.tavily_client import TavilyClient
from src.tools.f1_tools import initialize_tools
from src.utils.cache import CacheManager, get_cache_manager
from src.vector_store.manager import VectorStoreManager


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    return Settings(
        openai_api_key="test-key",
        openai_model="gpt-4-turbo",
        openai_temperature=0.7,
        openai_embedding_model="text-embedding-3-small",
        pinecone_api_key="test-key",
        pinecone_environment="test",
        pinecone_index_name="test-index",
        tavily_api_key="test-key",
        environment="test",
    )


@pytest.fixture
def mock_vector_store(mock_settings):
    """Create mock vector store."""
    with patch("src.vector_store.manager.Pinecone"):
        with patch("src.vector_store.manager.OpenAIEmbeddings"):
            vector_store = VectorStoreManager(mock_settings)
            vector_store._vector_store = MagicMock()
            return vector_store


@pytest.fixture
def mock_tavily_client(mock_settings):
    """Create mock Tavily client."""
    return TavilyClient(mock_settings, enable_cache=True)


@pytest.mark.asyncio
async def test_tools_initialization(
    mock_settings, mock_vector_store, mock_tavily_client
):
    """Test that tools are properly initialized with dependencies."""
    # Initialize tools
    initialize_tools(mock_settings, mock_vector_store, mock_tavily_client)

    # Import tools to verify they're accessible
    from src.tools.f1_tools import (
        _tavily_client,
        _vector_store_manager,
        search_current_f1_data,
    )

    assert _tavily_client is not None
    assert _vector_store_manager is not None
    assert search_current_f1_data is not None


@pytest.mark.asyncio
async def test_agent_graph_initialization(
    mock_settings, mock_vector_store, mock_tavily_client
):
    """Test that agent graph initializes with all components."""
    # Create agent graph
    agent = F1AgentGraph(
        config=mock_settings,
        vector_store=mock_vector_store,
        tavily_client=mock_tavily_client,
    )

    # Verify components are initialized
    assert agent.vector_store is not None
    assert agent.tavily_client is not None
    assert agent.llm is not None
    assert agent.analysis_llm is not None
    assert agent.graph is not None

    # Compile graph
    agent.compile()
    assert agent.compiled_graph is not None


@pytest.mark.asyncio
async def test_cache_manager_initialization():
    """Test that cache manager initializes correctly."""
    cache_manager = CacheManager()

    assert cache_manager.vector_cache is not None
    assert cache_manager.search_cache is not None
    assert cache_manager.llm_cache is not None

    # Test cache operations
    cache_manager.vector_cache.set("test_key", "test_value")
    assert cache_manager.vector_cache.get("test_key") == "test_value"

    # Test stats
    stats = cache_manager.get_all_stats()
    assert "vector_cache" in stats
    assert "search_cache" in stats
    assert "llm_cache" in stats


@pytest.mark.asyncio
async def test_global_cache_manager():
    """Test global cache manager singleton."""
    manager1 = get_cache_manager()
    manager2 = get_cache_manager()

    # Should be the same instance
    assert manager1 is manager2


@pytest.mark.asyncio
async def test_tavily_client_with_cache(mock_settings):
    """Test Tavily client caching functionality."""
    client = TavilyClient(mock_settings, enable_cache=True)

    # Mock the search tool
    mock_results = [
        {
            "title": "Test Result",
            "url": "https://test.com",
            "content": "Test content",
            "score": 0.9,
        }
    ]

    with patch.object(client, "search_tool") as mock_tool:
        mock_tool.ainvoke = AsyncMock(return_value=mock_results)

        # First call should hit the API
        results1 = await client.search("test query", use_cache=True)
        assert len(results1) == 1
        assert mock_tool.ainvoke.call_count == 1

        # Second call should use cache
        results2 = await client.search("test query", use_cache=True)
        assert len(results2) == 1
        assert mock_tool.ainvoke.call_count == 1  # Still 1, not 2


@pytest.mark.asyncio
async def test_vector_store_with_cache(mock_settings, mock_vector_store):
    """Test vector store caching functionality."""
    # Mock similarity search
    mock_docs = [
        Document(page_content="Test doc 1", metadata={"source": "test"}),
        Document(page_content="Test doc 2", metadata={"source": "test"}),
    ]

    mock_vector_store._vector_store.similarity_search = MagicMock(
        return_value=mock_docs
    )

    # First call
    results1 = await mock_vector_store.similarity_search("test query", use_cache=True)
    assert len(results1) == 2

    # Second call should use cache
    results2 = await mock_vector_store.similarity_search("test query", use_cache=True)
    assert len(results2) == 2

    # Verify cache was used (only one actual call to vector store)
    assert mock_vector_store._vector_store.similarity_search.call_count == 1


@pytest.mark.asyncio
async def test_agent_state_flow(mock_settings, mock_vector_store, mock_tavily_client):
    """Test that agent state flows correctly through the graph."""
    # Create initial state
    state = create_initial_state(session_id="test-session")

    assert state.session_id == "test-session"
    assert len(state.messages) == 0
    assert state.query == ""
    assert state.intent is None

    # Update state
    state.query = "Who won the 2024 championship?"
    state.intent = "current_info"

    assert state.query == "Who won the 2024 championship?"
    assert state.intent == "current_info"


@pytest.mark.asyncio
async def test_cache_key_generation():
    """Test cache key generation for different operations."""
    cache_manager = CacheManager()

    # Vector search cache key
    key1 = cache_manager.get_vector_cache_key("test query", 5, {"year": 2024})
    key2 = cache_manager.get_vector_cache_key("test query", 5, {"year": 2024})
    key3 = cache_manager.get_vector_cache_key("test query", 10, {"year": 2024})

    assert key1 == key2  # Same parameters should generate same key
    assert key1 != key3  # Different parameters should generate different key

    # Search cache key
    search_key1 = cache_manager.get_search_cache_key("test", 5, "advanced")
    search_key2 = cache_manager.get_search_cache_key("test", 5, "advanced")

    assert search_key1 == search_key2

    # LLM cache key
    llm_key1 = cache_manager.get_llm_cache_key("query", "context", "gpt-4", 0.7)
    llm_key2 = cache_manager.get_llm_cache_key("query", "context", "gpt-4", 0.7)

    assert llm_key1 == llm_key2


@pytest.mark.asyncio
async def test_cache_ttl_expiration():
    """Test that cache entries expire after TTL."""
    import time

    from src.utils.cache import TTLCache

    # Create cache with 1 second TTL
    cache = TTLCache(max_size=100, default_ttl=1)

    # Set value
    cache.set("test_key", "test_value")

    # Should be available immediately
    assert cache.get("test_key") == "test_value"

    # Wait for expiration
    time.sleep(1.1)

    # Should be expired
    assert cache.get("test_key") is None


@pytest.mark.asyncio
async def test_cache_lru_eviction():
    """Test LRU eviction when cache is full."""
    from src.utils.cache import TTLCache

    # Create small cache
    cache = TTLCache(max_size=3, default_ttl=300)

    # Fill cache
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")

    assert len(cache) == 3

    # Add one more (should evict key1)
    cache.set("key4", "value4")

    assert len(cache) == 3
    assert cache.get("key1") is None  # Evicted
    assert cache.get("key4") == "value4"  # New entry


@pytest.mark.asyncio
async def test_cache_stats():
    """Test cache statistics tracking."""
    from src.utils.cache import TTLCache

    cache = TTLCache(max_size=100, default_ttl=300)

    # Set some values
    cache.set("key1", "value1")
    cache.set("key2", "value2")

    # Generate hits and misses
    cache.get("key1")  # Hit
    cache.get("key1")  # Hit
    cache.get("key3")  # Miss

    stats = cache.get_stats()

    assert stats["size"] == 2
    assert stats["hits"] == 2
    assert stats["misses"] == 1
    assert stats["hit_rate"] == 2 / 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""Pytest configuration and fixtures.

This module provides reusable fixtures and utilities for testing the F1 Slipstream Agent.
Fixtures are organized into categories:
- Configuration: test_settings
- Mock Factories: mock_openai_embeddings, mock_openai_chat, mock_pinecone_index, etc.
- Test Data: sample_documents, sample_messages, sample_search_results, etc.
- Utilities: Helper functions for creating test data

When to Use Each Fixture:
-------------------------
- Use mock fixtures (mock_*) for unit tests that don't need real API calls
- Use sample data fixtures (sample_*) for consistent test data across tests
- Use utility functions (create_mock_*) when you need custom test data
- Use test_settings for any test that needs configuration access

Example Usage:
--------------
    # Unit test with mocks
    def test_embeddings(mock_openai_embeddings):
        result = mock_openai_embeddings.embed_query("test")
        assert len(result) == 1536

    # Integration test with sample data
    def test_document_processing(sample_documents):
        processor = DocumentProcessor()
        result = processor.process(sample_documents)
        assert len(result) > 0

    # Custom test data with utilities
    def test_custom_scenario():
        doc = create_mock_document("Custom content", {"year": 2024})
        assert doc.page_content == "Custom content"
"""

import os
from typing import Any, AsyncGenerator, Dict, Generator, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage

from src.config.settings import Settings


@pytest.fixture
def test_settings() -> Generator[Settings, None, None]:
    """Provide test settings with mock API keys.

    Use this fixture when your test needs access to application settings
    without requiring real API keys. Automatically cleans up after the test.

    When to use:
        - Testing configuration-dependent code
        - Testing code that accesses settings via get_settings()
        - Any test that needs environment variables set

    Example:
        >>> def test_api_client(test_settings):
        ...     client = APIClient(test_settings)
        ...     assert client.api_key == "test-openai-key"

    Yields:
        Settings: Test configuration instance with mock API keys
    """
    # Set test environment variables
    os.environ["OPENAI_API_KEY"] = "test-openai-key"
    os.environ["PINECONE_API_KEY"] = "test-pinecone-key"
    os.environ["PINECONE_ENVIRONMENT"] = "test-environment"
    os.environ["TAVILY_API_KEY"] = "test-tavily-key"
    os.environ["ENVIRONMENT"] = "development"
    os.environ["LOG_LEVEL"] = "DEBUG"

    # Clear the lru_cache to force reload with test values
    from src.config.settings import get_settings

    get_settings.cache_clear()

    settings = Settings()
    yield settings

    # Cleanup
    get_settings.cache_clear()


# ============================================================================
# Mock Factories for External APIs
# ============================================================================


@pytest.fixture
def mock_openai_embeddings() -> Mock:
    """Create mock OpenAI embeddings client.

    Use this fixture for unit tests that need embedding functionality
    without making actual API calls to OpenAI. Returns consistent
    1536-dimensional embeddings (matching text-embedding-ada-002).

    When to use:
        - Unit testing vector store operations
        - Testing document embedding logic
        - Testing similarity search without real embeddings

    Example:
        >>> def test_embed_documents(mock_openai_embeddings):
        ...     embeddings = mock_openai_embeddings.embed_documents(["doc1", "doc2"])
        ...     assert len(embeddings) == 2
        ...     assert len(embeddings[0]) == 1536

    Returns:
        Mock: Mock embeddings client with embed_documents, embed_query,
              aembed_documents, and aembed_query methods
    """
    mock = Mock()
    mock.embed_documents = Mock(return_value=[[0.1] * 1536 for _ in range(3)])
    mock.embed_query = Mock(return_value=[0.1] * 1536)
    mock.aembed_documents = AsyncMock(return_value=[[0.1] * 1536 for _ in range(3)])
    mock.aembed_query = AsyncMock(return_value=[0.1] * 1536)
    return mock


@pytest.fixture
def mock_openai_chat() -> Mock:
    """Create mock OpenAI chat client.

    Use this fixture for unit tests that need LLM chat functionality
    without making actual API calls. Returns consistent test responses.

    When to use:
        - Testing agent conversation logic
        - Testing prompt formatting and response handling
        - Testing streaming responses

    Example:
        >>> def test_chat_response(mock_openai_chat):
        ...     response = mock_openai_chat.invoke([HumanMessage(content="Hello")])
        ...     assert "test response" in response.content.lower()
        ...
        >>> async def test_streaming(mock_openai_chat):
        ...     chunks = [chunk async for chunk in mock_openai_chat.astream([])]
        ...     assert len(chunks) == 5

    Returns:
        Mock: Mock chat client with invoke, ainvoke, and astream methods
    """
    mock = Mock()
    mock_response = AIMessage(content="This is a test response from the LLM.")
    mock.invoke = Mock(return_value=mock_response)
    mock.ainvoke = AsyncMock(return_value=mock_response)

    # Mock streaming
    async def mock_astream(
        *args: Any, **kwargs: Any
    ) -> AsyncGenerator[AIMessage, None]:
        chunks = ["This ", "is ", "a ", "test ", "response."]
        for chunk in chunks:
            yield AIMessage(content=chunk)

    mock.astream = mock_astream
    return mock


@pytest.fixture
def mock_pinecone_index() -> Mock:
    """Create mock Pinecone index.

    Use this fixture for unit tests that interact with Pinecone
    without requiring a real index. Returns realistic query results
    with F1-related content.

    When to use:
        - Testing vector store upsert operations
        - Testing similarity search queries
        - Testing index statistics retrieval

    Example:
        >>> def test_vector_upsert(mock_pinecone_index):
        ...     result = mock_pinecone_index.upsert(vectors=[...])
        ...     assert result["upserted_count"] == 10
        ...
        >>> def test_similarity_query(mock_pinecone_index):
        ...     results = mock_pinecone_index.query(vector=[0.1]*1536, top_k=2)
        ...     assert len(results["matches"]) == 2
        ...     assert results["matches"][0]["score"] > 0.9

    Returns:
        Mock: Mock Pinecone index with upsert, query, and describe_index_stats methods
    """
    mock = Mock()
    mock.upsert = Mock(return_value={"upserted_count": 10})
    mock.query = Mock(
        return_value={
            "matches": [
                {
                    "id": "doc1",
                    "score": 0.95,
                    "metadata": {
                        "text": "Lewis Hamilton won the 2020 championship",
                        "year": 2020,
                        "category": "championship",
                    },
                },
                {
                    "id": "doc2",
                    "score": 0.87,
                    "metadata": {
                        "text": "Max Verstappen won the 2021 championship",
                        "year": 2021,
                        "category": "championship",
                    },
                },
            ]
        }
    )
    mock.describe_index_stats = Mock(
        return_value={
            "dimension": 1536,
            "index_fullness": 0.1,
            "total_vector_count": 1000,
        }
    )
    return mock


@pytest.fixture
def mock_tavily_client() -> Mock:
    """Create mock Tavily search client.

    Use this fixture for unit tests that need web search functionality
    without making actual API calls to Tavily. Returns realistic F1 search results.

    When to use:
        - Testing search result processing
        - Testing agent search node logic
        - Testing search result ranking and filtering

    Example:
        >>> def test_search(mock_tavily_client):
        ...     results = mock_tavily_client.search("F1 race results")
        ...     assert len(results["results"]) == 2
        ...     assert results["results"][0]["score"] > 0.9
        ...
        >>> async def test_async_search(mock_tavily_client):
        ...     results = await mock_tavily_client.search_async("F1 standings")
        ...     assert len(results["results"]) == 1

    Returns:
        Mock: Mock Tavily client with search and search_async methods
    """
    mock = Mock()
    mock.search = Mock(
        return_value={
            "results": [
                {
                    "title": "F1 Race Results",
                    "url": "https://formula1.com/results",
                    "content": "Max Verstappen won the latest race",
                    "score": 0.95,
                    "published_date": "2024-03-15",
                },
                {
                    "title": "F1 Standings",
                    "url": "https://formula1.com/standings",
                    "content": "Current championship standings",
                    "score": 0.88,
                    "published_date": "2024-03-14",
                },
            ]
        }
    )
    mock.search_async = AsyncMock(
        return_value={
            "results": [
                {
                    "title": "F1 Race Results",
                    "url": "https://formula1.com/results",
                    "content": "Max Verstappen won the latest race",
                    "score": 0.95,
                    "published_date": "2024-03-15",
                }
            ]
        }
    )
    return mock


@pytest.fixture
def mock_vector_store() -> Mock:
    """Create mock vector store manager.

    Use this fixture for unit tests that need vector store operations
    without requiring a real Pinecone connection. Returns realistic
    F1-related documents with similarity scores.

    When to use:
        - Testing RAG retrieval logic
        - Testing document addition workflows
        - Testing similarity search with scores

    Example:
        >>> async def test_similarity_search(mock_vector_store):
        ...     docs = await mock_vector_store.similarity_search("Hamilton")
        ...     assert len(docs) == 2
        ...     assert "championship" in docs[0].page_content.lower()
        ...
        >>> async def test_add_documents(mock_vector_store):
        ...     doc_ids = await mock_vector_store.add_documents([doc1, doc2])
        ...     assert len(doc_ids) == 3

    Returns:
        Mock: Mock vector store with similarity_search, add_documents,
              and similarity_search_with_score async methods
    """
    mock = Mock()
    mock.similarity_search = AsyncMock(
        return_value=[
            Document(
                page_content="Lewis Hamilton won the 2020 championship",
                metadata={"year": 2020, "category": "championship", "source": "test"},
            ),
            Document(
                page_content="Max Verstappen won the 2021 championship",
                metadata={"year": 2021, "category": "championship", "source": "test"},
            ),
        ]
    )
    mock.add_documents = AsyncMock(return_value=["doc1", "doc2", "doc3"])
    mock.similarity_search_with_score = AsyncMock(
        return_value=[(Document(page_content="Test doc", metadata={}), 0.95)]
    )
    return mock


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def sample_documents() -> List[Document]:
    """Provide sample F1 documents for testing.

    Use this fixture when you need consistent test documents across
    multiple tests. Contains documents about drivers, championships, and circuits.

    When to use:
        - Testing document processing pipelines
        - Testing metadata enrichment
        - Testing document filtering and search

    Example:
        >>> def test_document_filter(sample_documents):
        ...     driver_docs = [d for d in sample_documents
        ...                    if d.metadata.get("category") == "driver_stats"]
        ...     assert len(driver_docs) == 1
        ...     assert "Hamilton" in driver_docs[0].page_content

    Returns:
        List[Document]: Three sample documents with F1 content and metadata
    """
    return [
        Document(
            page_content="Lewis Hamilton is a seven-time Formula 1 World Champion.",
            metadata={
                "source": "test",
                "category": "driver_stats",
                "year": 2020,
                "driver": "Lewis Hamilton",
            },
        ),
        Document(
            page_content="Max Verstappen won the 2021 and 2022 championships.",
            metadata={
                "source": "test",
                "category": "championship",
                "year": 2022,
                "driver": "Max Verstappen",
            },
        ),
        Document(
            page_content="Monaco Grand Prix is held on the streets of Monte Carlo.",
            metadata={
                "source": "test",
                "category": "circuit",
                "race": "Monaco Grand Prix",
            },
        ),
    ]


@pytest.fixture
def sample_messages() -> List[Any]:
    """Provide sample conversation messages.

    Use this fixture when testing conversation flows, memory management,
    or message processing. Contains a realistic back-and-forth conversation.

    When to use:
        - Testing conversation memory
        - Testing message history processing
        - Testing context window management

    Example:
        >>> def test_conversation_length(sample_messages):
        ...     assert len(sample_messages) == 4
        ...     human_msgs = [m for m in sample_messages if isinstance(m, HumanMessage)]
        ...     assert len(human_msgs) == 2

    Returns:
        List[BaseMessage]: Four messages alternating between human and AI
    """
    return [
        HumanMessage(content="Who won the 2021 championship?"),
        AIMessage(content="Max Verstappen won the 2021 Formula 1 World Championship."),
        HumanMessage(content="What about 2020?"),
        AIMessage(content="Lewis Hamilton won the 2020 championship."),
    ]


@pytest.fixture
def sample_search_results() -> List[Dict[str, Any]]:
    """Provide sample web search results.

    Use this fixture when testing search result processing without
    making actual API calls. Contains realistic F1 search results.

    When to use:
        - Testing search result parsing
        - Testing result ranking and filtering
        - Testing search result formatting

    Example:
        >>> def test_search_ranking(sample_search_results):
        ...     sorted_results = sorted(sample_search_results,
        ...                            key=lambda x: x["score"], reverse=True)
        ...     assert sorted_results[0]["score"] == 0.92

    Returns:
        List[Dict]: Two sample search results with titles, URLs, content, and scores
    """
    return [
        {
            "title": "F1 2024 Season Preview",
            "url": "https://formula1.com/2024-preview",
            "content": "The 2024 season promises exciting battles between top teams.",
            "score": 0.92,
            "published_date": "2024-01-15",
        },
        {
            "title": "Latest F1 News",
            "url": "https://formula1.com/news",
            "content": "Breaking news from the world of Formula 1.",
            "score": 0.85,
            "published_date": "2024-03-10",
        },
    ]


@pytest.fixture
def sample_agent_state() -> Dict[str, Any]:
    """Provide sample agent state for testing agent workflows.

    Use this fixture when testing agent nodes or state transitions.
    Contains a complete agent state with all required fields.

    When to use:
        - Testing agent node functions
        - Testing state transitions
        - Testing agent graph execution

    Example:
        >>> def test_agent_node(sample_agent_state):
        ...     result = process_query_node(sample_agent_state)
        ...     assert result["intent"] is not None
        ...     assert "query" in result

    Returns:
        Dict: Complete agent state with messages, query, intent, and metadata
    """
    return {
        "messages": [HumanMessage(content="Who won the last race?")],
        "query": "Who won the last race?",
        "intent": "current_results",
        "entities": {"race": "latest"},
        "retrieved_docs": [],
        "search_results": [],
        "context": "",
        "response": None,
        "metadata": {
            "session_id": "test-session-123",
            "timestamp": "2024-03-15T10:00:00Z",
        },
    }


# ============================================================================
# Async Test Utilities
# ============================================================================


@pytest.fixture
def event_loop():
    """Create event loop for async tests.

    Use this fixture when writing async tests. Pytest-asyncio typically
    handles this automatically, but this fixture ensures compatibility.

    When to use:
        - Async tests that need explicit event loop control
        - Tests that create multiple async tasks
        - Tests with complex async setup/teardown

    Example:
        >>> async def test_async_operation(event_loop):
        ...     result = await some_async_function()
        ...     assert result is not None

    Yields:
        Event loop: Asyncio event loop for test execution
    """
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Test Database/Vector Store Setup
# ============================================================================


@pytest.fixture
async def test_vector_store_index(test_settings: Settings) -> AsyncGenerator[str, None]:
    """Create a test Pinecone index for integration tests.

    Note: This fixture requires actual Pinecone credentials for integration tests.
    For unit tests, use mock_vector_store instead.

    When to use:
        - Integration tests that need a real Pinecone index
        - End-to-end tests with actual vector operations
        - Performance testing with real data

    When NOT to use:
        - Unit tests (use mock_vector_store instead)
        - Tests that don't need real vector operations
        - CI/CD pipelines without Pinecone credentials

    Example:
        >>> async def test_real_vector_store(test_vector_store_index):
        ...     # This test requires PINECONE_API_KEY in environment
        ...     index_name = test_vector_store_index
        ...     # Perform real vector operations...

    Args:
        test_settings: Test settings with Pinecone configuration

    Yields:
        str: Test index name (automatically cleaned up after test)
    """
    # This would create a real test index for integration tests
    # For now, we'll just yield a test index name
    test_index_name = f"test-{test_settings.pinecone_index_name}"

    # Setup: Create test index (would require actual Pinecone client)
    # For unit tests, this is skipped

    yield test_index_name

    # Teardown: Delete test index
    # For unit tests, this is skipped


# ============================================================================
# Mock Context Managers
# ============================================================================


class MockAsyncContextManager:
    """Mock async context manager for testing."""

    def __init__(self, return_value: Any = None):
        """Initialize mock context manager.

        Args:
            return_value: Value to return on enter
        """
        self.return_value = return_value

    async def __aenter__(self) -> Any:
        """Enter context."""
        return self.return_value

    async def __aexit__(self, *args: Any) -> None:
        """Exit context."""
        pass


@pytest.fixture
def mock_async_context() -> type[MockAsyncContextManager]:
    """Provide mock async context manager for testing async with statements.

    Use this fixture when testing code that uses async context managers
    without requiring actual async resources.

    When to use:
        - Testing async database connections
        - Testing async file operations
        - Testing async resource management

    Example:
        >>> async def test_async_context(mock_async_context):
        ...     mock_resource = {"data": "test"}
        ...     async with mock_async_context(mock_resource) as resource:
        ...         assert resource["data"] == "test"

    Returns:
        MockAsyncContextManager: Mock context manager class that can be instantiated
    """
    return MockAsyncContextManager


# ============================================================================
# Test Utility Functions (moved from test_utils.py)
# ============================================================================


def create_mock_document(
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    doc_id: Optional[str] = None,
) -> Document:
    """Create a mock document for testing.

    Use this utility when you need to create test documents without loading
    actual data. Useful for unit tests that validate document processing logic.

    Args:
        content: Document content
        metadata: Document metadata (optional)
        doc_id: Document ID (optional, will be added to metadata)

    Returns:
        Document: Mock document with specified content and metadata

    Example:
        >>> doc = create_mock_document("Test content", {"year": 2024}, "doc-123")
        >>> assert doc.page_content == "Test content"
        >>> assert doc.metadata["id"] == "doc-123"
    """
    if metadata is None:
        metadata = {}

    doc = Document(page_content=content, metadata=metadata)
    if doc_id:
        doc.metadata["id"] = doc_id

    return doc


def create_mock_messages(conversation: List[tuple[str, str]]) -> List[Any]:
    """Create mock conversation messages from simple tuples.

    Use this utility to quickly create message sequences for testing
    conversation flows and agent state management.

    Args:
        conversation: List of (role, content) tuples where role is "user" or "assistant"

    Returns:
        List[BaseMessage]: List of HumanMessage and AIMessage objects

    Example:
        >>> messages = create_mock_messages([
        ...     ("user", "Hello"),
        ...     ("assistant", "Hi there!")
        ... ])
        >>> assert len(messages) == 2
        >>> assert isinstance(messages[0], HumanMessage)
    """
    messages = []
    for role, content in conversation:
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))

    return messages


def create_mock_search_result(
    title: str = "Test Result",
    url: str = "https://test.com",
    content: str = "Test content",
    score: float = 0.9,
) -> Dict[str, Any]:
    """Create a mock search result for testing search functionality.

    Use this utility when testing search result processing without
    making actual API calls to Tavily or other search services.

    Args:
        title: Result title (default: "Test Result")
        url: Result URL (default: "https://test.com")
        content: Result content (default: "Test content")
        score: Relevance score (default: 0.9)

    Returns:
        Dict: Mock search result with standard fields

    Example:
        >>> result = create_mock_search_result(
        ...     title="F1 News",
        ...     score=0.95
        ... )
        >>> assert result["title"] == "F1 News"
        >>> assert result["score"] == 0.95
    """
    return {
        "title": title,
        "url": url,
        "content": content,
        "score": score,
        "published_date": "2024-03-15",
    }


def assert_document_equal(doc1: Document, doc2: Document) -> None:
    """Assert two documents are equal in content and metadata.

    Use this utility for cleaner test assertions when comparing documents.
    Provides better error messages than direct comparison.

    Args:
        doc1: First document
        doc2: Second document

    Raises:
        AssertionError: If documents differ in content or metadata

    Example:
        >>> doc1 = create_mock_document("Test", {"year": 2024})
        >>> doc2 = create_mock_document("Test", {"year": 2024})
        >>> assert_document_equal(doc1, doc2)  # Passes
    """
    assert doc1.page_content == doc2.page_content
    assert doc1.metadata == doc2.metadata


def assert_message_equal(msg1: Any, msg2: Any) -> None:
    """Assert two messages are equal in type and content.

    Use this utility when comparing message objects in conversation tests.
    Validates both message type and content.

    Args:
        msg1: First message
        msg2: Second message

    Raises:
        AssertionError: If messages differ in type or content

    Example:
        >>> msg1 = HumanMessage(content="Hello")
        >>> msg2 = HumanMessage(content="Hello")
        >>> assert_message_equal(msg1, msg2)  # Passes
    """
    assert type(msg1) == type(msg2)
    assert msg1.content == msg2.content


def create_mock_llm_response(content: str = "Test response") -> AIMessage:
    """Create a mock LLM response message.

    Use this utility when testing code that processes LLM responses
    without making actual API calls.

    Args:
        content: Response content (default: "Test response")

    Returns:
        AIMessage: Mock LLM response

    Example:
        >>> response = create_mock_llm_response("The answer is 42")
        >>> assert response.content == "The answer is 42"
    """
    return AIMessage(content=content)


def create_mock_embedding(dimension: int = 1536) -> List[float]:
    """Create a mock embedding vector for testing.

    Use this utility when testing embedding-related functionality
    without calling actual embedding APIs. Default dimension matches
    OpenAI's text-embedding-ada-002 model.

    Args:
        dimension: Embedding dimension (default: 1536)

    Returns:
        List[float]: Mock embedding vector of specified dimension

    Example:
        >>> embedding = create_mock_embedding(dimension=768)
        >>> assert len(embedding) == 768
        >>> assert all(v == 0.1 for v in embedding)
    """
    return [0.1] * dimension


class MockStreamingResponse:
    """Mock streaming response for testing async streaming functionality.

    Use this class when testing code that processes streaming responses
    from LLMs or other async streaming sources.

    Example:
        >>> async def test_streaming():
        ...     stream = MockStreamingResponse(["Hello", " ", "world"])
        ...     chunks = [chunk async for chunk in stream]
        ...     assert chunks == ["Hello", " ", "world"]
    """

    def __init__(self, chunks: List[str]):
        """Initialize mock streaming response.

        Args:
            chunks: List of response chunks to stream
        """
        self.chunks = chunks
        self.index = 0

    def __aiter__(self):
        """Return async iterator."""
        return self

    async def __anext__(self) -> str:
        """Get next chunk.

        Returns:
            str: Next chunk

        Raises:
            StopAsyncIteration: When no more chunks available
        """
        if self.index >= len(self.chunks):
            raise StopAsyncIteration

        chunk = self.chunks[self.index]
        self.index += 1
        return chunk


class AsyncMockIterator:
    """Async iterator mock for testing async iteration patterns.

    Use this class when testing code that iterates over async iterables
    without requiring actual async data sources.

    Example:
        >>> async def test_async_iteration():
        ...     iterator = AsyncMockIterator([1, 2, 3])
        ...     items = [item async for item in iterator]
        ...     assert items == [1, 2, 3]
    """

    def __init__(self, items: List[Any]):
        """Initialize async iterator.

        Args:
            items: Items to iterate over
        """
        self.items = items
        self.index = 0

    def __aiter__(self):
        """Return async iterator."""
        return self

    async def __anext__(self) -> Any:
        """Get next item.

        Returns:
            Any: Next item

        Raises:
            StopAsyncIteration: When no more items available
        """
        if self.index >= len(self.items):
            raise StopAsyncIteration

        item = self.items[self.index]
        self.index += 1
        return item

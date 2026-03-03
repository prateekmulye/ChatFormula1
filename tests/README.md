# Chat P1 Tests

This directory contains a streamlined test suite for the Chat P1 agent system, focusing on tests that provide clear value in catching bugs and documenting behavior.

## Test Structure

The test suite contains 18 test files organized by functionality:

```
tests/
├── conftest.py                          # Pytest configuration and shared fixtures
├── test_config.py                       # Configuration tests
├── test_exceptions.py                   # Exception handling tests
├── test_security.py                     # Security feature tests
├── test_document_processor.py           # Document processing unit tests
├── test_data_loader.py                  # Data loading unit tests
├── test_prompts.py                      # Prompt template unit tests
├── test_fallback.py                     # Fallback mechanism unit tests
├── test_tavily_client.py                # Tavily client unit tests
├── test_integration_vector_store.py     # Vector store integration tests
├── test_integration_tavily.py           # Tavily search integration tests
├── test_integration_api.py              # API endpoint integration tests
├── test_integration_agent.py            # Agent flow integration tests
├── test_integration_complete.py         # Complete integration tests
└── test_e2e_user_workflows.py          # End-to-end user workflow tests
```

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
Fast, isolated tests that validate individual components using mocks for external dependencies.

**Files:** test_config.py, test_exceptions.py, test_document_processor.py, test_data_loader.py, test_prompts.py, test_fallback.py, test_tavily_client.py

### Integration Tests (`@pytest.mark.integration`)
Tests that validate component interactions with real external services (requires test credentials).

**Files:** test_integration_vector_store.py, test_integration_tavily.py, test_integration_api.py, test_integration_agent.py, test_integration_complete.py

### End-to-End Tests (`@pytest.mark.e2e`)
Complete user workflow tests that simulate real user interactions across the entire system.

**Files:** test_e2e_user_workflows.py

### Security Tests (`@pytest.mark.security`)
Tests that validate authentication, authorization, input validation, and other security features.

**Files:** test_security.py

## Running Tests

### Run All Tests
```bash
poetry run pytest
```

### Run by Category
```bash
# Unit tests only (fast, no external dependencies)
poetry run pytest -m unit

# Integration tests only (requires real API keys)
poetry run pytest -m integration

# E2E tests only (requires all services)
poetry run pytest -m e2e

# Security tests only
poetry run pytest -m security
```

### Run Specific Test File
```bash
poetry run pytest tests/test_document_processor.py
```

### Run with Coverage
```bash
poetry run pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### Run with Verbose Output
```bash
poetry run pytest -v
```

### Run Tests in Parallel
```bash
poetry run pytest -n auto
```

## Environment Setup

### For Unit Tests
Unit tests use mock API keys and don't require real credentials:
```bash
export OPENAI_API_KEY="test-openai-key"
export PINECONE_API_KEY="test-pinecone-key"
export PINECONE_ENVIRONMENT="test-environment"
export TAVILY_API_KEY="test-tavily-key"
```

### For Integration and E2E Tests
Integration and E2E tests require real API credentials:
```bash
export OPENAI_API_KEY="your-real-openai-key"
export PINECONE_API_KEY="your-real-pinecone-key"
export PINECONE_ENVIRONMENT="your-pinecone-environment"
export TAVILY_API_KEY="your-real-tavily-key"
```

Or use a `.env` file in the project root.

## Test Fixtures

### Common Fixtures (from `conftest.py`)

- `test_settings`: Provides test configuration with mock API keys
- `mock_openai_embeddings`: Mock OpenAI embeddings client
- `mock_openai_chat`: Mock OpenAI chat client
- `mock_pinecone_index`: Mock Pinecone index
- `mock_tavily_client`: Mock Tavily search client
- `mock_vector_store`: Mock vector store manager
- `sample_documents`: Sample LangChain documents
- `sample_messages`: Sample conversation messages
- `sample_search_results`: Sample search results
- `sample_agent_state`: Sample agent state

### Using Fixtures

```python
@pytest.mark.unit
def test_example(test_settings, sample_documents):
    """Example test using fixtures."""
    processor = DocumentProcessor(test_settings)
    result = processor.process_documents(sample_documents)
    assert len(result) > 0
```

## Test Utilities

Shared test utilities and fixtures are available in `conftest.py`. See the "Test Fixtures" section below for details on available fixtures and helper functions.

## Skipping Tests

Tests that require real API credentials will automatically skip if mock credentials are detected:

```python
if test_settings.pinecone_api_key.startswith("test-"):
    pytest.skip("Skipping integration test - no real Pinecone API key")
```

## Continuous Integration

For CI/CD pipelines:

```bash
# Run only unit tests (fast, no external dependencies)
poetry run pytest -m unit --cov=src --cov-report=xml

# Run integration tests (requires test credentials)
poetry run pytest -m integration

# Run all tests
poetry run pytest --cov=src --cov-report=xml
```

## Test Coverage

View coverage report:
```bash
poetry run pytest --cov=src --cov-report=html
open htmlcov/index.html
```

Target coverage: 80%+

## Writing New Tests

### Unit Test Template

```python
import pytest
from src.module import MyClass

@pytest.mark.unit
class TestMyClass:
    """Unit tests for MyClass."""
    
    def test_basic_functionality(self, test_settings):
        """Test basic functionality."""
        obj = MyClass(test_settings)
        result = obj.method()
        assert result is not None
```

### Integration Test Template

```python
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
class TestMyIntegration:
    """Integration tests for my feature."""
    
    async def test_integration(self, test_settings):
        """Test integration."""
        if test_settings.api_key.startswith("test-"):
            pytest.skip("Skipping - no real API key")
        
        # Test code here
        assert True
```

### E2E Test Template

```python
import pytest

@pytest.mark.e2e
@pytest.mark.asyncio
class TestUserWorkflow:
    """E2E tests for user workflow."""
    
    async def test_complete_workflow(self, agent):
        """Test complete user workflow."""
        # Simulate user interaction
        result = await agent.run(state)
        assert result is not None
```

## Troubleshooting

### Tests Failing Due to Missing Dependencies
```bash
poetry install
```

### Tests Failing Due to Missing API Keys
- Check your `.env` file
- Verify environment variables are set
- For unit tests, mock keys should work
- For integration/E2E tests, real keys are required

### Async Tests Not Running
Ensure `pytest-asyncio` is installed:
```bash
poetry add --group dev pytest-asyncio
```

### Import Errors
Make sure you're running tests from the project root:
```bash
cd apps/f1-slipstream-agent
poetry run pytest
```

## Best Practices

1. **Keep unit tests fast** - Use mocks for external dependencies, aim for <10 seconds total execution time
2. **Test one thing at a time** - Each test should verify a single behavior
3. **Use descriptive names** - Test names should describe what they test and what the expected outcome is
4. **Arrange-Act-Assert** - Structure tests clearly with setup, execution, and verification phases
5. **Clean up resources** - Use fixtures for setup/teardown to avoid test pollution
6. **Mark tests appropriately** - Use `@pytest.mark.unit`, `@pytest.mark.integration`, etc. for proper test organization
7. **Test error cases** - Don't just test happy paths, verify error handling and edge cases
8. **Document complex tests** - Add docstrings explaining what's being tested and why
9. **Maintain test data** - Keep test fixtures up to date and realistic
10. **Review test value regularly** - Remove tests that don't catch bugs or document important behavior

## Contributing

When adding new features:
1. Write unit tests first (TDD approach recommended)
2. Add integration tests for external service interactions
3. Add E2E tests for critical user-facing workflows
4. Ensure all tests pass before submitting PR
5. Maintain or improve code coverage (target: 70%+ on core modules)
6. Follow the "What Makes a Good Test" guidelines above
7. Remove or update tests that become obsolete

## What Makes a Good Test

The test suite follows these principles to ensure tests provide real value:

### Write Tests That:
1. **Test behavior, not implementation** - Focus on what the code does, not how it does it. Avoid testing private methods or internal structure.
2. **Test real functionality** - Use real objects and minimal mocking. Tests should validate actual system behavior, not mock behavior.
3. **Have clear value** - Each test should catch a specific type of bug or document important behavior. Ask: "What bug would this test catch?"
4. **Are easy to understand** - Test names and code should be self-documenting. A developer should understand what's being tested by reading the test name.
5. **Are maintainable** - Simple setup, clear assertions, minimal dependencies. If a test is hard to understand, it's hard to maintain.

### Avoid Tests That:
1. **Test obvious behavior** - Don't test that framework features work (e.g., testing that LangChain's prompt templates work).
2. **Duplicate coverage** - One test per behavior is enough. Multiple tests for the same thing add maintenance burden without value.
3. **Test implementation details** - Don't test internal structure, private methods, or how something is implemented.
4. **Are overly complex** - If a test requires deep understanding of multiple unrelated components, it's too complex.
5. **Test edge cases with low probability** - Focus on realistic scenarios that users will actually encounter.

### Test Structure Best Practices:
- **Arrange-Act-Assert**: Structure tests clearly with setup, execution, and verification phases
- **One assertion per test**: Each test should verify a single behavior (though multiple assertions for the same behavior are fine)
- **Descriptive names**: Use names like `test_document_processor_splits_long_text_into_chunks` not `test_process`
- **Clear failure messages**: When a test fails, it should be obvious what went wrong
- **Minimal setup**: Use fixtures for common setup, but keep test-specific setup in the test itself

### When to Write Each Type of Test:

**Unit Tests** - Write when:
- Testing a single component in isolation
- Testing business logic or data transformations
- Testing error handling for specific conditions
- You need fast feedback during development

**Integration Tests** - Write when:
- Testing interactions between components
- Testing external API integrations
- Testing database operations
- Verifying that components work together correctly

**E2E Tests** - Write when:
- Testing complete user workflows
- Verifying the system works end-to-end
- Testing critical user journeys
- You need confidence that features work from the user's perspective

### Examples of Good vs. Bad Tests:

**Good Test:**
```python
@pytest.mark.unit
def test_document_processor_splits_text_exceeding_chunk_size():
    """Document processor should split text longer than chunk_size into multiple chunks."""
    processor = DocumentProcessor(chunk_size=100)
    long_text = "a" * 250
    chunks = processor.process(long_text)
    assert len(chunks) >= 3
    assert all(len(chunk) <= 100 for chunk in chunks)
```

**Bad Test:**
```python
@pytest.mark.unit
def test_document_processor_has_chunk_size_attribute():
    """Test that DocumentProcessor has chunk_size attribute."""
    processor = DocumentProcessor(chunk_size=100)
    assert hasattr(processor, 'chunk_size')  # Tests implementation detail
    assert processor.chunk_size == 100  # Tests obvious behavior
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [LangChain Testing Guide](https://python.langchain.com/docs/contributing/testing)

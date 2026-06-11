"""Tests for the model-agnostic provider factory.

The factory matrix: provider (openai | ollama | openai_compatible) ×
base URL (default | explicit) × credentials (real | dummy). All clients
are constructed without network access, so every case runs keyless.
"""

from typing import Any

import pytest

from chatf1_agent.providers import (
    DUMMY_API_KEY,
    GENERATION_TAG,
    OLLAMA_CLOUD_BASE_URL,
    OLLAMA_LOCAL_BASE_URL,
    create_analysis_llm,
    create_embeddings,
    create_generation_llm,
)
from chatf1_agent.settings import Settings


def make_settings(**overrides: Any) -> Settings:
    """Settings from the dummy test environment plus explicit overrides."""
    return Settings(_env_file=None, **overrides)


@pytest.mark.unit
class TestChatFactoryMatrix:
    """Provider × base_url × credentials for the chat models."""

    def test_openai_defaults(self):
        """OpenAI uses the library-default endpoint and the real key."""
        llm = create_generation_llm(make_settings())

        assert llm.openai_api_base is None
        assert llm.openai_api_key is not None
        assert llm.openai_api_key.get_secret_value() == "test-openai-key"
        assert llm.model_name == "gpt-4o-mini"
        assert llm.streaming is True
        assert llm.tags == [GENERATION_TAG]

    def test_openai_missing_key_fails_fast(self, monkeypatch: pytest.MonkeyPatch):
        """The OpenAI provider refuses to construct without a key."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        with pytest.raises(ValueError, match="openai_api_key"):
            create_generation_llm(make_settings())

    def test_ollama_local_defaults(self):
        """Ollama defaults to the local /v1 endpoint with the dummy key."""
        llm = create_generation_llm(
            make_settings(llm_provider="ollama", llm_model="qwen3:8b")
        )

        assert llm.openai_api_base == OLLAMA_LOCAL_BASE_URL
        assert llm.openai_api_key is not None
        assert llm.openai_api_key.get_secret_value() == DUMMY_API_KEY
        assert llm.model_name == "qwen3:8b"
        assert llm.tags == [GENERATION_TAG]

    def test_ollama_needs_no_openai_key(self, monkeypatch: pytest.MonkeyPatch):
        """Local Ollama runs entirely keyless."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        llm = create_generation_llm(make_settings(llm_provider="ollama"))

        assert llm.openai_api_key is not None
        assert llm.openai_api_key.get_secret_value() == DUMMY_API_KEY

    def test_ollama_cloud_base_url_and_key(self):
        """Ollama Cloud is an explicit base URL plus a real key."""
        llm = create_generation_llm(
            make_settings(
                llm_provider="ollama",
                llm_base_url=OLLAMA_CLOUD_BASE_URL,
                llm_api_key="ollama-cloud-key",
                llm_model="gpt-oss:120b",
            )
        )

        assert llm.openai_api_base == OLLAMA_CLOUD_BASE_URL
        assert llm.openai_api_key is not None
        assert llm.openai_api_key.get_secret_value() == "ollama-cloud-key"

    def test_openai_compatible_requires_base_url(self):
        """A generic compatible endpoint has no default to guess."""
        with pytest.raises(ValueError, match="llm_base_url"):
            create_generation_llm(make_settings(llm_provider="openai_compatible"))

    def test_openai_compatible_with_base_url(self):
        """An explicit compatible endpoint constructs with the dummy key."""
        llm = create_generation_llm(
            make_settings(
                llm_provider="openai_compatible",
                llm_base_url="http://vllm.internal:8000/v1",
                llm_model="meta-llama/Llama-3.1-8B-Instruct",
            )
        )

        assert llm.openai_api_base == "http://vllm.internal:8000/v1"
        assert llm.openai_api_key is not None
        assert llm.openai_api_key.get_secret_value() == DUMMY_API_KEY

    def test_settings_load_from_environment(self, monkeypatch: pytest.MonkeyPatch):
        """Provider selection is reachable purely through env vars."""
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        monkeypatch.setenv("LLM_MODEL", "llama3.2:3b")

        llm = create_generation_llm(Settings(_env_file=None))

        assert llm.openai_api_base == OLLAMA_LOCAL_BASE_URL
        assert llm.model_name == "llama3.2:3b"


@pytest.mark.unit
class TestAnalysisModel:
    """The analysis model shares the chat endpoint but stays untagged."""

    def test_defaults_to_generation_model(self):
        """With no override, analysis uses the generation model at temp 0."""
        llm = create_analysis_llm(make_settings())

        assert llm.model_name == "gpt-4o-mini"
        assert llm.temperature == 0.0
        assert not llm.tags or GENERATION_TAG not in llm.tags

    def test_explicit_analysis_model(self):
        """llm_analysis_model overrides the generation model."""
        llm = create_analysis_llm(
            make_settings(llm_model="gpt-4o", llm_analysis_model="gpt-4o-mini")
        )

        assert llm.model_name == "gpt-4o-mini"

    def test_analysis_follows_provider_endpoint(self):
        """The analysis model targets the same provider endpoint."""
        llm = create_analysis_llm(make_settings(llm_provider="ollama"))

        assert llm.openai_api_base == OLLAMA_LOCAL_BASE_URL


@pytest.mark.unit
class TestFunctionCallingCapability:
    """Capability flag defaults per provider, overridable either way."""

    @pytest.mark.parametrize(
        ("provider", "override", "expected"),
        [
            ("openai", None, True),
            ("ollama", None, False),
            ("openai_compatible", None, False),
            ("ollama", True, True),
            ("openai", False, False),
        ],
    )
    def test_capability_matrix(
        self, provider: str, override: bool | None, expected: bool
    ):
        """supports_function_calling: provider default unless overridden."""
        settings = make_settings(
            llm_provider=provider,
            llm_supports_function_calling=override,
        )

        assert settings.supports_function_calling is expected

    def test_override_via_environment(self, monkeypatch: pytest.MonkeyPatch):
        """The override is reachable through the environment."""
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        monkeypatch.setenv("LLM_SUPPORTS_FUNCTION_CALLING", "true")

        assert Settings(_env_file=None).supports_function_calling is True


@pytest.mark.unit
class TestEmbeddingFactory:
    """Embedding endpoint, model, and dimension resolution."""

    def test_openai_defaults(self):
        """OpenAI embeddings: default endpoint, 1536 implied, ctx check on."""
        settings = make_settings()
        embeddings = create_embeddings(settings)

        assert embeddings.openai_api_base is None
        assert embeddings.model == "text-embedding-3-small"
        assert embeddings.check_embedding_ctx_length is True
        assert embeddings.dimensions is None
        assert settings.resolved_embedding_dimension == 1536

    def test_openai_explicit_dimension_is_forwarded(self):
        """An explicit dimension reaches the OpenAI client (3-small/large)."""
        embeddings = create_embeddings(make_settings(embedding_dimension=256))

        assert embeddings.dimensions == 256

    def test_embeddings_follow_chat_provider(self):
        """Without embedding_provider, embeddings inherit the chat endpoint."""
        embeddings = create_embeddings(
            make_settings(
                llm_provider="ollama",
                embedding_model="nomic-embed-text",
                embedding_dimension=768,
            )
        )

        assert embeddings.openai_api_base == OLLAMA_LOCAL_BASE_URL
        assert embeddings.openai_api_key is not None
        assert embeddings.openai_api_key.get_secret_value() == DUMMY_API_KEY
        assert embeddings.check_embedding_ctx_length is False

    def test_embeddings_inherit_chat_base_url_and_key(self):
        """Inherited provider also inherits the chat base URL and key."""
        embeddings = create_embeddings(
            make_settings(
                llm_provider="ollama",
                llm_base_url=OLLAMA_CLOUD_BASE_URL,
                llm_api_key="ollama-cloud-key",
                embedding_model="nomic-embed-text",
                embedding_dimension=768,
            )
        )

        assert embeddings.openai_api_base == OLLAMA_CLOUD_BASE_URL
        assert embeddings.openai_api_key is not None
        assert embeddings.openai_api_key.get_secret_value() == "ollama-cloud-key"

    def test_split_providers_do_not_leak_endpoints(self):
        """An explicit embedding provider ignores the chat endpoint."""
        embeddings = create_embeddings(
            make_settings(
                llm_provider="openai_compatible",
                llm_base_url="http://vllm.internal:8000/v1",
                embedding_provider="ollama",
                embedding_model="mxbai-embed-large",
                embedding_dimension=1024,
            )
        )

        assert embeddings.openai_api_base == OLLAMA_LOCAL_BASE_URL
        assert embeddings.model == "mxbai-embed-large"

    def test_missing_dimension_fails_loudly(self):
        """Non-OpenAI embeddings without a dimension are a config error."""
        settings = make_settings(
            llm_provider="ollama",
            embedding_model="nomic-embed-text",
        )

        with pytest.raises(ValueError) as exc_info:
            create_embeddings(settings)

        message = str(exc_info.value)
        assert "EMBEDDING_DIMENSION" in message
        assert "768" in message
        assert "make reindex" in message

    def test_embedding_dimension_via_environment(self, monkeypatch: pytest.MonkeyPatch):
        """The dimension is reachable through the environment."""
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
        monkeypatch.setenv("EMBEDDING_DIMENSION", "768")

        settings = Settings(_env_file=None)

        assert settings.resolved_embedding_dimension == 768
        assert create_embeddings(settings).check_embedding_ctx_length is False

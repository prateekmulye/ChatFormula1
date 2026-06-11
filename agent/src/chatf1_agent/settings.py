"""Application settings loaded from environment variables.

API keys default to empty strings so importing any module — and running the
test suite — never requires credentials. Code that actually talks to an
external service calls :meth:`Settings.require` at construction time.
"""

import json
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Agent service settings.

    Never instantiate at import time; call :func:`get_settings` inside the
    code paths that need configuration.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Credentials (validated lazily via `require`, never at import time)
    openai_api_key: str = Field(default="", description="OpenAI API key")
    pinecone_api_key: str = Field(default="", description="Pinecone API key")
    tavily_api_key: str = Field(default="", description="Tavily Search API key")
    internal_api_token: str = Field(
        default="",
        description="Static bearer token required on all /internal routes",
    )

    # ── Model provider ──────────────────────────────────────────────────
    # The agent speaks the OpenAI wire protocol to every provider; these
    # settings only pick the endpoint and capabilities. Resolution rules
    # live in chatf1_agent/providers.py; the reasoning lives in
    # docs/adr/002-model-agnostic-providers.md.
    llm_provider: Literal["openai", "ollama", "openai_compatible"] = Field(
        default="openai",
        description="Chat-model provider: openai, ollama, or any OpenAI-compatible endpoint",
    )
    llm_base_url: str | None = Field(
        default=None,
        description=(
            "Chat endpoint override. None uses the provider default "
            "(api.openai.com for openai, http://localhost:11434/v1 for ollama; "
            "Ollama Cloud is https://ollama.com/v1). Required for openai_compatible."
        ),
    )
    llm_api_key: str = Field(
        default="",
        description=(
            "API key for non-OpenAI chat providers (e.g. Ollama Cloud). "
            "Local servers that ignore auth get a dummy key automatically."
        ),
    )
    llm_model: str = Field(
        default="gpt-4o-mini",
        description="Model used for answer generation",
    )
    llm_analysis_model: str = Field(
        default="",
        description="Model used for query analysis (empty = use llm_model)",
    )
    llm_supports_function_calling: bool | None = Field(
        default=None,
        description=(
            "Whether the chat model supports function-calling structured output. "
            "None = provider default (true for openai, false otherwise). When "
            "false, query analysis uses a prompted-JSON path instead."
        ),
    )
    llm_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Temperature for answer generation",
    )
    llm_max_tokens: int = Field(
        default=1000,
        ge=100,
        le=4000,
        description="Maximum tokens for LLM completion",
    )

    # ── Embeddings (may target a different provider than the chat models) ─
    embedding_provider: Literal["openai", "ollama", "openai_compatible"] | None = Field(
        default=None,
        description="Embedding provider (None = follow llm_provider)",
    )
    embedding_base_url: str | None = Field(
        default=None,
        description="Embedding endpoint override (None = provider default)",
    )
    embedding_api_key: str = Field(
        default="",
        description="API key for the embedding endpoint when it differs from the chat key",
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Embedding model name",
    )
    embedding_dimension: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Vector dimension produced by embedding_model. None is only valid "
            "for OpenAI (1536, text-embedding-3-small); it MUST be explicit "
            "for every other provider — e.g. nomic-embed-text=768, "
            "mxbai-embed-large=1024. The Pinecone index is created with and "
            "validated against this value."
        ),
    )

    # Pinecone
    pinecone_index_name: str = Field(
        default="f1-knowledge",
        description="Pinecone index name",
    )

    # Tavily
    tavily_max_results: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum search results from Tavily",
    )
    tavily_search_depth: Literal["basic", "advanced"] = Field(
        default="advanced",
        description="Tavily search depth",
    )
    tavily_include_domains: str | list[str] = Field(
        default_factory=lambda: [
            "formula1.com",
            "fia.com",
            "autosport.com",
            "motorsport.com",
            "racefans.net",
            "the-race.com",
            "espn.com/f1",
            "bbc.com/sport/formula1",
            "skysports.com/f1",
        ],
        description="Preferred domains for F1 news (empty list = all domains)",
    )
    tavily_exclude_domains: str | list[str] = Field(
        default_factory=list,
        description="Domains to exclude from search results",
    )

    # Application
    app_name: str = Field(default="ChatFormula1", description="Application name")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )
    environment: Literal["development", "test", "staging", "production"] = Field(
        default="development",
        description="Application environment",
    )
    max_conversation_history: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum history messages forwarded to the LLM",
    )

    # RAG
    vector_search_top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of documents to retrieve from the vector store",
    )
    chunk_size: int = Field(
        default=1000,
        ge=100,
        le=2000,
        description="Document chunk size for ingestion",
    )
    chunk_overlap: int = Field(
        default=200,
        ge=0,
        le=500,
        description="Overlap between document chunks",
    )

    @field_validator(
        "tavily_include_domains",
        "tavily_exclude_domains",
        mode="before",
    )
    @classmethod
    def parse_string_lists(cls, v: object) -> object:
        """Parse list fields from JSON, comma-separated, or single-value env strings."""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            if v.startswith("["):
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            if "," in v:
                return [item.strip() for item in v.split(",") if item.strip()]
            return [v]
        return v if v is not None else []

    @property
    def analysis_model(self) -> str:
        """Model used for query analysis; defaults to the generation model."""
        return self.llm_analysis_model or self.llm_model

    @property
    def supports_function_calling(self) -> bool:
        """Whether the chat model can honor function-calling structured output.

        Explicit ``llm_supports_function_calling`` wins; otherwise only the
        OpenAI provider is assumed capable, and everything else gets the
        prompted-JSON analysis path.
        """
        if self.llm_supports_function_calling is not None:
            return self.llm_supports_function_calling
        return self.llm_provider == "openai"

    @property
    def resolved_embedding_provider(self) -> str:
        """Embedding provider, following llm_provider unless set explicitly."""
        return self.embedding_provider or self.llm_provider

    @property
    def resolved_embedding_dimension(self) -> int:
        """Embedding dimension the Pinecone index must match.

        The dimension travels with the embedding model: vectors from
        different models are not interchangeable, so a provider switch
        without an explicit dimension is a configuration error, not
        something to guess at.

        Raises:
            ValueError: If the provider is not OpenAI and no explicit
                ``embedding_dimension`` was configured.
        """
        if self.embedding_dimension is not None:
            return self.embedding_dimension
        if self.resolved_embedding_provider == "openai":
            return 1536  # text-embedding-3-small
        raise ValueError(
            "EMBEDDING_DIMENSION must be set explicitly when the embedding "
            f"provider is '{self.resolved_embedding_provider}' — the index "
            "dimension travels with the embedding model. Common values: "
            "nomic-embed-text=768, mxbai-embed-large=1024, "
            "text-embedding-3-small=1536. After changing it, rebuild the "
            "index with `make reindex` BEFORE re-ingesting."
        )

    @property
    def is_development(self) -> bool:
        """Check if running in the development environment."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in the production environment."""
        return self.environment == "production"

    def require(self, *fields: str) -> None:
        """Raise if any of the named credential fields is unset.

        Args:
            *fields: Settings field names that must be non-empty.

        Raises:
            ValueError: If a required credential is missing or a placeholder.
        """
        missing = [
            name
            for name in fields
            if not getattr(self, name) or str(getattr(self, name)).startswith("your_")
        ]
        if missing:
            raise ValueError(
                f"Missing required settings: {', '.join(missing)}. "
                "Set them in the environment or .env file."
            )


@lru_cache
def get_settings() -> Settings:
    """Get the cached settings instance."""
    return Settings()

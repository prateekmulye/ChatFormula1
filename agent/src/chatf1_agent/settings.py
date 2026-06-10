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

    # LLM configuration (gpt-4o-mini for both generation and analysis)
    generation_model: str = Field(
        default="gpt-4o-mini",
        description="Model used for answer generation",
    )
    analysis_model: str = Field(
        default="gpt-4o-mini",
        description="Model used for structured query analysis",
    )
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model",
    )
    openai_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Temperature for answer generation",
    )
    openai_max_tokens: int = Field(
        default=1000,
        ge=100,
        le=4000,
        description="Maximum tokens for LLM completion",
    )

    # Pinecone
    pinecone_index_name: str = Field(
        default="f1-knowledge",
        description="Pinecone index name",
    )
    pinecone_dimension: int = Field(
        default=1536,
        description="Embedding dimension for the Pinecone index",
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

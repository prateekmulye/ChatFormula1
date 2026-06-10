"""Pydantic-based configuration management with environment variable loading."""

import json
from functools import lru_cache
from typing import Literal, Optional, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # OpenAI Configuration
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_model: str = Field(
        default="gpt-4-turbo",
        description="OpenAI model to use for generation",
    )
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model",
    )
    openai_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Temperature for LLM generation",
    )
    openai_max_tokens: Optional[int] = Field(
        default=1000,
        ge=100,
        le=4000,
        description="Maximum tokens for LLM completion",
    )
    openai_streaming: bool = Field(
        default=True,
        description="Enable streaming responses for faster perceived performance",
    )

    # Pinecone Configuration
    pinecone_api_key: str = Field(..., description="Pinecone API key")
    pinecone_environment: Optional[str] = Field(
        default=None,
        description="Pinecone environment (deprecated in v3.0+, kept for compatibility)",
    )
    pinecone_index_name: str = Field(
        default="f1-knowledge",
        description="Pinecone index name",
    )
    pinecone_dimension: int = Field(
        default=1536,
        description="Embedding dimension for Pinecone index",
    )

    # Tavily Configuration
    tavily_api_key: str = Field(..., description="Tavily Search API key")
    tavily_max_results: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum search results from Tavily",
    )
    tavily_search_depth: Literal["basic", "advanced"] = Field(
        default="advanced",
        description="Tavily search depth (advanced includes more sources)",
    )
    tavily_include_domains: Union[str, list[str]] = Field(
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
    tavily_exclude_domains: Union[str, list[str]] = Field(
        default_factory=list,
        description="Domains to exclude from search results",
    )
    tavily_include_answer: bool = Field(
        default=True,
        description="Include AI-generated answer in search results",
    )
    tavily_include_raw_content: bool = Field(
        default=True,
        description="Include raw content for ingestion into vector DB",
    )
    tavily_include_images: bool = Field(
        default=False,
        description="Include images in search results",
    )
    tavily_max_crawl_depth: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Maximum depth for Tavily crawl operations",
    )

    # Application Configuration
    app_name: str = Field(default="ChatFormula1", description="Application name")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )
    max_conversation_history: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum conversation history to maintain",
    )
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application environment",
    )

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, ge=1024, le=65535, description="API port")
    api_reload: bool = Field(
        default=True,
        description="Enable auto-reload for development",
    )

    # RAG Configuration
    vector_search_top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of documents to retrieve from vector store",
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

    # Retry Configuration
    max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts for API calls",
    )
    retry_delay: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Initial delay between retries in seconds",
    )

    # Security Configuration
    enable_rate_limiting: bool = Field(
        default=True,
        description="Enable rate limiting for API endpoints",
    )
    rate_limit_per_minute: int = Field(
        default=60,
        ge=1,
        le=1000,
        description="Maximum requests per minute per client",
    )
    rate_limit_per_hour: int = Field(
        default=1000,
        ge=1,
        le=10000,
        description="Maximum requests per hour per client",
    )
    enable_input_validation: bool = Field(
        default=True,
        description="Enable input validation and sanitization",
    )
    strict_input_validation: bool = Field(
        default=False,
        description="Use strict input validation (more restrictive)",
    )
    max_query_length: int = Field(
        default=2000,
        ge=100,
        le=10000,
        description="Maximum query length in characters",
    )
    enable_cors: bool = Field(
        default=True,
        description="Enable CORS middleware",
    )
    cors_allow_origins: Union[str, list[str]] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:8501",
            "http://localhost:8000",
        ],
        description="Allowed CORS origins",
    )
    require_api_key: bool = Field(
        default=False,
        description="Require API key for all endpoints (except public paths)",
    )
    api_key_header_name: str = Field(
        default="X-API-Key",
        description="Header name for API key",
    )

    @field_validator("openai_api_key", "pinecone_api_key", "tavily_api_key")
    @classmethod
    def validate_api_keys(cls, v: str, info) -> str:
        """Validate that API keys are not empty or placeholder values."""
        if not v or v.startswith("your_") or v == "":
            raise ValueError(
                f"{info.field_name} must be set to a valid API key. "
                f"Please update your .env file."
            )
        return v

    @field_validator(
        "cors_allow_origins",
        "tavily_include_domains",
        "tavily_exclude_domains",
        mode="before",
    )
    @classmethod
    def parse_string_lists(cls, v):
        """Parse list fields from environment variables.

        Supports:
        - List objects (from code): ["item1", "item2"]
        - JSON strings: '["item1","item2"]'
        - Comma-separated: "item1,item2"
        - Single string: "*" or "item1"
        - Empty string: returns empty list
        """
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            # Handle empty string
            if not v:
                return []
            # Handle wildcard (for CORS)
            if v == "*":
                return ["*"]
            # Try parsing as JSON
            if v.startswith("["):
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            # Try comma-separated
            if "," in v:
                return [item.strip() for item in v.split(",") if item.strip()]
            # Single value
            return [v]
        return v if v is not None else []

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Settings: Application settings instance

    Raises:
        ValidationError: If configuration is invalid
    """
    return Settings()

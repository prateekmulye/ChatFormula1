"""Model-agnostic chat and embedding factory.

This module is the single seam between the agent and whatever serves its
models. Three decisions shape it:

1. **One wire protocol, many providers.** Every provider this app targets —
   OpenAI, Ollama (local or cloud), vLLM, LM Studio, OpenRouter — speaks the
   OpenAI chat/embeddings API. So instead of one integration package per
   vendor, the factory always builds ``langchain-openai`` clients and varies
   only ``base_url``, ``api_key``, and capability flags. Switching providers
   is a settings change, never a code change.

2. **Capabilities are configuration, not model-name heuristics.**
   ``Settings.supports_function_calling`` tells the graph whether the model
   can honor ``with_structured_output``; when it can't (most local models),
   the graph drops to a prompted-JSON analysis path. The factory never
   branches on model names.

3. **The embedding dimension travels with the provider.** Embeddings from
   different models are not interchangeable, so ``create_embeddings``
   resolves the dimension eagerly — a provider switch without an explicit
   ``embedding_dimension`` fails at construction, not at query time.

Both chat models (generation + analysis) and the embedding client MUST be
built here. The generation model is tagged ``["generation"]`` — the
streaming server forwards ``on_chat_model_stream`` events only for that
tag, which keeps the analysis model's output off the user-visible stream.
Constructing a model anywhere else would bypass that contract.
"""

from typing import Any

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from chatf1_agent.settings import Settings

GENERATION_TAG = "generation"

# Ollama's OpenAI-compatible endpoints. The local URL is applied
# automatically for `llm_provider=ollama`; Ollama Cloud is opt-in via
# LLM_BASE_URL because it needs an API key and hosts a different catalog.
OLLAMA_LOCAL_BASE_URL = "http://localhost:11434/v1"
OLLAMA_CLOUD_BASE_URL = "https://ollama.com/v1"

# OpenAI client libraries refuse to start without *some* API key, but local
# servers (Ollama, LM Studio, vLLM) never check it. Convention is "ollama".
DUMMY_API_KEY = "ollama"

# Batch size for embedding requests (matches the OpenAI API sweet spot and
# is harmless for local servers, which just see smaller payloads).
EMBEDDING_BATCH_SIZE = 100


def _resolve_endpoint(
    provider: str,
    base_url: str | None,
    api_key: str,
    settings: Settings,
    base_url_setting: str,
) -> tuple[str | None, str]:
    """Resolve (base_url, api_key) for one OpenAI-compatible endpoint.

    Args:
        provider: One of ``openai``, ``ollama``, ``openai_compatible``.
        base_url: Explicit endpoint override, if any.
        api_key: Explicit key for non-OpenAI providers, if any.
        settings: Application settings (for the OpenAI credential check).
        base_url_setting: Settings field name to cite in error messages.

    Returns:
        ``(base_url, api_key)`` ready to hand to a langchain-openai client.
        ``base_url=None`` means the client's default (api.openai.com).

    Raises:
        ValueError: If credentials or a required base URL are missing.
    """
    if provider == "openai":
        settings.require("openai_api_key")
        return base_url, settings.openai_api_key

    if provider == "ollama":
        return base_url or OLLAMA_LOCAL_BASE_URL, api_key or DUMMY_API_KEY

    # openai_compatible: there is no sane default endpoint to guess.
    if not base_url:
        raise ValueError(
            f"{base_url_setting} must be set when the provider is "
            "'openai_compatible' — there is no default endpoint to assume. "
            "Point it at your server's OpenAI-compatible /v1 root."
        )
    return base_url, api_key or DUMMY_API_KEY


def resolve_chat_endpoint(settings: Settings) -> tuple[str | None, str]:
    """Resolve the chat-model endpoint from settings."""
    return _resolve_endpoint(
        provider=settings.llm_provider,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        settings=settings,
        base_url_setting="llm_base_url",
    )


def resolve_embedding_endpoint(settings: Settings) -> tuple[str | None, str]:
    """Resolve the embedding endpoint from settings.

    When ``embedding_provider`` is unset, embeddings follow the chat
    endpoint entirely (provider, base URL, and key); explicit embedding
    settings always win.
    """
    base_url = settings.embedding_base_url
    api_key = settings.embedding_api_key
    if settings.embedding_provider is None:
        base_url = base_url or settings.llm_base_url
        api_key = api_key or settings.llm_api_key
    return _resolve_endpoint(
        provider=settings.resolved_embedding_provider,
        base_url=base_url,
        api_key=api_key,
        settings=settings,
        base_url_setting="embedding_base_url",
    )


def create_generation_llm(settings: Settings) -> ChatOpenAI:
    """Create the streaming chat model used for answer generation.

    Args:
        settings: Application settings (provider, model, temperature, limits).

    Returns:
        A streaming chat model tagged ``["generation"]`` for stream filtering.
    """
    base_url, api_key = resolve_chat_endpoint(settings)
    return ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        streaming=True,
        stream_usage=True,
        timeout=30,
        tags=[GENERATION_TAG],
    )


def create_analysis_llm(settings: Settings) -> ChatOpenAI:
    """Create the deterministic chat model used for query analysis.

    Deliberately untagged: its output (function-calling or prompted JSON)
    must never reach the user-visible token stream.

    Args:
        settings: Application settings (provider, analysis model).

    Returns:
        A temperature-0 chat model for structured or JSON-mode analysis.
    """
    base_url, api_key = resolve_chat_endpoint(settings)
    return ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=settings.analysis_model,
        temperature=0.0,
        timeout=30,
    )


def create_embeddings(settings: Settings) -> OpenAIEmbeddings:
    """Create the embedding client for the configured provider.

    Resolves the embedding dimension eagerly so a misconfigured provider
    switch fails here, loudly, instead of corrupting the vector index.

    Args:
        settings: Application settings (embedding provider, model, dimension).

    Returns:
        An embedding client targeting the configured endpoint.

    Raises:
        ValueError: If the dimension is unresolvable or credentials are
            missing (see :meth:`Settings.resolved_embedding_dimension`).
    """
    provider = settings.resolved_embedding_provider
    base_url, api_key = resolve_embedding_endpoint(settings)
    _ = settings.resolved_embedding_dimension  # fail fast, loudly

    kwargs: dict[str, Any] = {
        "api_key": api_key,
        "base_url": base_url,
        "model": settings.embedding_model,
        "chunk_size": EMBEDDING_BATCH_SIZE,
        "max_retries": 3,
    }
    if provider == "openai":
        # text-embedding-3-* accept a server-side dimension override; only
        # forward it when the operator chose one explicitly.
        if settings.embedding_dimension is not None:
            kwargs["dimensions"] = settings.embedding_dimension
    else:
        # Non-OpenAI servers (Ollama included) reject tiktoken token arrays
        # on /v1/embeddings — send raw strings and skip the context-length
        # precheck, which is OpenAI-specific anyway.
        kwargs["check_embedding_ctx_length"] = False

    return OpenAIEmbeddings(**kwargs)

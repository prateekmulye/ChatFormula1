"""LLM factory seam.

Both the generation and analysis models default to gpt-4o-mini and are
configured exclusively through :class:`~chatf1_agent.settings.Settings`,
so swapping providers or models is a one-line settings change.

The generation model is tagged ``["generation"]`` — the streaming server
forwards ``on_chat_model_stream`` events only for that tag, which keeps the
analysis model's structured-output JSON out of the user-visible stream.
"""

from langchain_openai import ChatOpenAI

from chatf1_agent.settings import Settings

GENERATION_TAG = "generation"


def create_generation_llm(settings: Settings) -> ChatOpenAI:
    """Create the streaming LLM used for answer generation.

    Args:
        settings: Application settings (model name, temperature, limits).

    Returns:
        A streaming ChatOpenAI instance tagged ``["generation"]``.
    """
    settings.require("openai_api_key")
    return ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.generation_model,
        temperature=settings.openai_temperature,
        max_tokens=settings.openai_max_tokens,
        streaming=True,
        stream_usage=True,
        timeout=30,
        tags=[GENERATION_TAG],
    )


def create_analysis_llm(settings: Settings) -> ChatOpenAI:
    """Create the deterministic LLM used for structured query analysis.

    Args:
        settings: Application settings (model name).

    Returns:
        A temperature-0 ChatOpenAI instance for structured output.
    """
    settings.require("openai_api_key")
    return ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.analysis_model,
        temperature=0.0,
        timeout=30,
    )

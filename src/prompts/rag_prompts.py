"""RAG (Retrieval-Augmented Generation) prompt templates.

This module contains prompts for combining retrieved context from vector stores
and search results with user queries to generate informed responses.
"""

from typing import List, Optional

from langchain_core.messages import SystemMessage
from langchain_core.prompts import (ChatPromptTemplate,
                                    HumanMessagePromptTemplate,
                                    MessagesPlaceholder, PromptTemplate)

# RAG prompt for combining vector context with queries
RAG_CONTEXT_TEMPLATE = """You are ChatFormula1, an expert Formula 1 analyst. Use the provided context to answer the user's question accurately.

**Context from Knowledge Base:**
{vector_context}

**Recent Information from Search:**
{search_context}

**Instructions:**
1. Synthesize information from both knowledge base and search results
2. Prioritize recent search results for current season information
3. Use knowledge base for historical context and statistics
4. Cite specific sources when making factual claims
5. If contexts conflict, note the discrepancy and explain
6. If context is insufficient, acknowledge limitations

**Citation Format:**
- For knowledge base: [Source: Historical Data, Year]
- For search results: [Source: {source_name}, {date}]

Now answer the user's question using the context above.
"""


def create_rag_prompt_template(
    include_conversation_history: bool = True,
) -> ChatPromptTemplate:
    """Create a RAG prompt template for context-aware responses.

    Args:
        include_conversation_history: Whether to include conversation history

    Returns:
        ChatPromptTemplate configured for RAG
    """
    messages = [
        SystemMessage(content="You are ChatFormula1, an expert Formula 1 analyst."),
    ]

    if include_conversation_history:
        messages.append(
            MessagesPlaceholder(variable_name="chat_history", optional=True)
        )

    messages.extend(
        [
            HumanMessagePromptTemplate.from_template(RAG_CONTEXT_TEMPLATE),
            HumanMessagePromptTemplate.from_template("User question: {query}"),
        ]
    )

    return ChatPromptTemplate.from_messages(messages)


# Prompt template for vector-only retrieval (when search is unavailable)
VECTOR_ONLY_TEMPLATE = """You are ChatFormula1, an expert Formula 1 analyst.

**Context from Knowledge Base:**
{vector_context}

**Note:** Real-time search is currently unavailable. Responses are based on historical knowledge base only.

**Instructions:**
1. Answer based on the provided historical context
2. Acknowledge if the question requires current information
3. Provide the most recent information available in the knowledge base
4. Suggest the user check official F1 sources for latest updates if needed

User question: {query}

Provide a helpful answer based on the available context.
"""

VECTOR_ONLY_PROMPT = PromptTemplate(
    template=VECTOR_ONLY_TEMPLATE,
    input_variables=["vector_context", "query"],
)


# Prompt template for search-only mode (when vector store is unavailable)
SEARCH_ONLY_TEMPLATE = """You are ChatFormula1, an expert Formula 1 analyst.

**Recent Information from Search:**
{search_context}

**Note:** Historical knowledge base is currently unavailable. Responses are based on recent search results only.

**Instructions:**
1. Answer based on the provided search results
2. Focus on current information and recent developments
3. Cite sources from search results
4. Acknowledge if historical context would enhance the answer

User question: {query}

Provide a helpful answer based on the available search results.
"""

SEARCH_ONLY_PROMPT = PromptTemplate(
    template=SEARCH_ONLY_TEMPLATE,
    input_variables=["search_context", "query"],
)


# Conversation-aware RAG prompt with history
CONVERSATIONAL_RAG_TEMPLATE = """You are ChatFormula1, an expert Formula 1 analyst engaged in a conversation.

**Retrieved Context:**
{context}

**Conversation History:**
{chat_history}

**Current Question:**
{query}

**Instructions:**
1. Consider the conversation history to understand context and follow-up questions
2. Use retrieved context to provide accurate, detailed answers
3. Reference previous exchanges when relevant
4. Maintain conversation continuity and coherence
5. Cite sources for factual claims

Provide a natural, conversational response that builds on the discussion.
"""

CONVERSATIONAL_RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content="You are ChatFormula1, an expert Formula 1 analyst."),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        HumanMessagePromptTemplate.from_template(
            """**Retrieved Context:**
{context}

**Current Question:**
{query}

Use the context above and our conversation history to answer the question."""
        ),
    ]
)


def format_vector_context(documents: List[dict]) -> str:
    """Format vector store documents into context string.

    Args:
        documents: List of retrieved documents with content and metadata

    Returns:
        Formatted context string
    """
    if not documents:
        return "No relevant historical context found."

    context_parts = []
    for i, doc in enumerate(documents, 1):
        content = doc.get("content", "")
        metadata = doc.get("metadata", {})

        source = metadata.get("source", "Unknown")
        year = metadata.get("year", "N/A")
        category = metadata.get("category", "General")

        context_parts.append(
            f"[Document {i}] ({category}, {year})\n"
            f"Source: {source}\n"
            f"Content: {content}\n"
        )

    return "\n---\n".join(context_parts)


def format_search_context(search_results: List[dict]) -> str:
    """Format search results into context string.

    Args:
        search_results: List of search results with title, content, url, date

    Returns:
        Formatted context string
    """
    if not search_results:
        return "No recent search results available."

    context_parts = []
    for i, result in enumerate(search_results, 1):
        title = result.get("title", "Untitled")
        content = result.get("content", "")
        url = result.get("url", "")
        date = result.get("published_date", "Recent")
        source = result.get("source", "Web")

        context_parts.append(
            f"[Result {i}] {title}\n"
            f"Source: {source} | Date: {date}\n"
            f"URL: {url}\n"
            f"Content: {content}\n"
        )

    return "\n---\n".join(context_parts)


def format_conversation_history(messages: List[dict], max_messages: int = 10) -> str:
    """Format conversation history for prompt inclusion.

    Args:
        messages: List of message dicts with 'role' and 'content'
        max_messages: Maximum number of recent messages to include

    Returns:
        Formatted conversation history string
    """
    if not messages:
        return "No previous conversation."

    # Take only the most recent messages
    recent_messages = messages[-max_messages:]

    formatted = []
    for msg in recent_messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        if role == "user":
            formatted.append(f"User: {content}")
        elif role == "assistant":
            formatted.append(f"Assistant: {content}")

    return "\n".join(formatted)


# Source attribution prompt addition
SOURCE_ATTRIBUTION_INSTRUCTION = """
**Source Attribution Requirements:**
- Always cite sources when presenting facts or statistics
- Use format: [Source: Name, Date/Year]
- For multiple sources, list all relevant citations
- Distinguish between historical data and recent information
- If information cannot be verified from provided context, state this clearly
"""


def create_rag_prompt_with_citations(
    vector_context: str,
    search_context: str,
    query: str,
    chat_history: Optional[str] = None,
) -> str:
    """Create a complete RAG prompt with all context and citation requirements.

    Args:
        vector_context: Formatted vector store context
        search_context: Formatted search results context
        query: User's question
        chat_history: Optional formatted conversation history

    Returns:
        Complete prompt string ready for LLM
    """
    prompt_parts = [
        "You are ChatFormula1, an expert Formula 1 analyst.",
        "",
        "**Context from Knowledge Base:**",
        vector_context,
        "",
        "**Recent Information from Search:**",
        search_context,
        "",
    ]

    if chat_history:
        prompt_parts.extend(
            [
                "**Conversation History:**",
                chat_history,
                "",
            ]
        )

    prompt_parts.extend(
        [
            SOURCE_ATTRIBUTION_INSTRUCTION,
            "",
            f"**User Question:** {query}",
            "",
            "Provide a comprehensive, well-cited answer using the context above.",
        ]
    )

    return "\n".join(prompt_parts)


# Prompt for handling insufficient context
INSUFFICIENT_CONTEXT_TEMPLATE = """You are ChatFormula1, an expert Formula 1 analyst.

**Available Context:**
{context}

**User Question:**
{query}

**Note:** The available context is limited or may not fully address the question.

**Instructions:**
1. Answer what you can based on available context
2. Clearly state what information is missing or uncertain
3. Suggest what additional information would be helpful
4. Offer to search for more current information if relevant
5. Provide general F1 knowledge if applicable

Be honest about limitations while still being helpful.
"""

INSUFFICIENT_CONTEXT_PROMPT = PromptTemplate(
    template=INSUFFICIENT_CONTEXT_TEMPLATE,
    input_variables=["context", "query"],
)


# Multi-source synthesis prompt
MULTI_SOURCE_SYNTHESIS_TEMPLATE = """You are ChatFormula1, synthesizing information from multiple sources.

**Historical Data:**
{historical_context}

**Current Season Data:**
{current_context}

**Recent News:**
{news_context}

**User Question:**
{query}

**Synthesis Instructions:**
1. Integrate information from all sources chronologically
2. Highlight trends and patterns across time periods
3. Note any conflicts or discrepancies between sources
4. Provide a cohesive narrative that connects past and present
5. Cite each source appropriately

Create a comprehensive answer that leverages all available information.
"""

MULTI_SOURCE_SYNTHESIS_PROMPT = PromptTemplate(
    template=MULTI_SOURCE_SYNTHESIS_TEMPLATE,
    input_variables=["historical_context", "current_context", "news_context", "query"],
)

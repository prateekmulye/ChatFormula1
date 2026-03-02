"""Prompt templates module for ChatFormula1 agent.

This module provides comprehensive prompt templates for:
- System prompts defining agent persona and guardrails
- RAG prompts for context-aware generation
- Specialized prompts for predictions, analysis, and structured outputs
"""

from .rag_prompts import (CONVERSATIONAL_RAG_PROMPT,
                          INSUFFICIENT_CONTEXT_PROMPT,
                          MULTI_SOURCE_SYNTHESIS_PROMPT, RAG_CONTEXT_TEMPLATE,
                          SEARCH_ONLY_PROMPT, SOURCE_ATTRIBUTION_INSTRUCTION,
                          VECTOR_ONLY_PROMPT, create_rag_prompt_template,
                          create_rag_prompt_with_citations,
                          format_conversation_history, format_search_context,
                          format_vector_context)
from .specialized_prompts import (CHAIN_OF_THOUGHT_PROMPT, COMPARISON_PROMPT,
                                  ENTITY_EXTRACTION_TEMPLATE,
                                  PREDICTION_TEMPLATE, QUERY_ANALYSIS_TEMPLATE,
                                  TECHNICAL_EXPLANATION_TEMPLATE,
                                  ExtractedEntities, QueryIntent,
                                  RacePrediction,
                                  create_chain_of_thought_prompt,
                                  create_entity_extraction_prompt,
                                  create_few_shot_prediction_prompt,
                                  create_few_shot_query_analysis_prompt,
                                  create_prediction_prompt,
                                  create_query_analysis_prompt,
                                  create_technical_explanation_prompt)
from .system_prompts import (CONCISE_SYSTEM_PROMPT, DETAILED_SYSTEM_PROMPT,
                             F1_EXPERT_SYSTEM_PROMPT,
                             OFF_TOPIC_GUARDRAIL_PROMPT,
                             PREDICTION_SYSTEM_PROMPT,
                             create_role_based_system_prompt,
                             create_system_prompt, validate_prompt_safety)

__all__ = [
    # System prompts
    "F1_EXPERT_SYSTEM_PROMPT",
    "OFF_TOPIC_GUARDRAIL_PROMPT",
    "CONCISE_SYSTEM_PROMPT",
    "DETAILED_SYSTEM_PROMPT",
    "PREDICTION_SYSTEM_PROMPT",
    "create_system_prompt",
    "create_role_based_system_prompt",
    "validate_prompt_safety",
    # RAG prompts
    "RAG_CONTEXT_TEMPLATE",
    "VECTOR_ONLY_PROMPT",
    "SEARCH_ONLY_PROMPT",
    "CONVERSATIONAL_RAG_PROMPT",
    "INSUFFICIENT_CONTEXT_PROMPT",
    "MULTI_SOURCE_SYNTHESIS_PROMPT",
    "SOURCE_ATTRIBUTION_INSTRUCTION",
    "create_rag_prompt_template",
    "format_vector_context",
    "format_search_context",
    "format_conversation_history",
    "create_rag_prompt_with_citations",
    # Specialized prompts
    "QueryIntent",
    "RacePrediction",
    "ExtractedEntities",
    "QUERY_ANALYSIS_TEMPLATE",
    "PREDICTION_TEMPLATE",
    "CHAIN_OF_THOUGHT_PROMPT",
    "COMPARISON_PROMPT",
    "TECHNICAL_EXPLANATION_TEMPLATE",
    "ENTITY_EXTRACTION_TEMPLATE",
    "create_query_analysis_prompt",
    "create_prediction_prompt",
    "create_few_shot_query_analysis_prompt",
    "create_few_shot_prediction_prompt",
    "create_chain_of_thought_prompt",
    "create_technical_explanation_prompt",
    "create_entity_extraction_prompt",
]

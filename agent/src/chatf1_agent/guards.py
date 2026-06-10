"""Prompt-injection heuristics for the LLM boundary.

Only LLM-adjacent checks live here. Transport-level validation (length
caps, HTML stripping, control characters, repeated-character DoS) is the
gateway's responsibility and is enforced there.
"""

import re

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

# Patterns that indicate an attempt to override the system prompt.
INJECTION_PATTERNS = [
    r"ignore\s+(?:(?:previous|above|all)\s+)+(?:instructions|prompts|rules)",
    r"system\s*:\s*you\s+are",
    r"<\s*\|\s*im_start\s*\|\s*>",
    r"<\s*\|\s*im_end\s*\|\s*>",
    r"###\s*instruction",
    r"###\s*system",
    r"forget\s+(?:everything|all|previous)",
    r"disregard\s+(?:(?:previous|all)\s+)+(?:instructions|prompts)",
    r"you\s+are\s+now\s+a",
    r"pretend\s+you\s+are",
    r"act\s+as\s+if",
    r"roleplay\s+as",
]

_COMPILED_PATTERNS = [
    re.compile(pattern, re.IGNORECASE) for pattern in INJECTION_PATTERNS
]


class GuardVerdict(BaseModel):
    """Result of a prompt-injection scan."""

    flagged: bool = Field(description="Whether the input matched an injection pattern")
    matched_pattern: str | None = Field(
        default=None,
        description="The regex pattern that matched, if any",
    )


def scan_for_prompt_injection(text: str) -> GuardVerdict:
    """Scan user input for prompt-injection attempts.

    Args:
        text: Raw user message.

    Returns:
        GuardVerdict with ``flagged=True`` if an injection pattern matched.
    """
    for pattern in _COMPILED_PATTERNS:
        if pattern.search(text):
            logger.warning(
                "prompt_injection_detected",
                pattern=pattern.pattern,
                input_preview=text[:100],
            )
            return GuardVerdict(flagged=True, matched_pattern=pattern.pattern)

    return GuardVerdict(flagged=False)

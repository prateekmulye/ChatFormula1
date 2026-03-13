"""Input validation and sanitization for security.

This module provides input validation and sanitization to prevent prompt injection,
XSS attacks, and other security vulnerabilities.
"""

import re
from typing import Optional

import structlog
from pydantic import BaseModel, Field, field_validator

logger = structlog.get_logger(__name__)

# Pre-compiled regular expressions for performance
_REPEATED_CHARS_RE = re.compile(r"(.)\1{50,}")
_WHITESPACE_RE = re.compile(r"[ \t]+")
_MULTIPLE_NEWLINES_RE = re.compile(r"\n{3,}")
_HTML_TAGS_RE = re.compile(r"<[^>]+>")


class ValidationResult(BaseModel):
    """Result of input validation."""

    valid: bool = Field(..., description="Whether input is valid")
    sanitized_input: Optional[str] = Field(None, description="Sanitized input if valid")
    errors: list[str] = Field(default_factory=list, description="Validation errors")
    warnings: list[str] = Field(default_factory=list, description="Validation warnings")


class InputValidator:
    """Validator for user input with security checks."""

    # Configuration
    MIN_LENGTH = 1
    MAX_LENGTH = 2000
    MAX_LINES = 50

    # Suspicious patterns that might indicate prompt injection
    SUSPICIOUS_PATTERNS = [
        re.compile(
            r"ignore\s+(previous|above|all)\s+(instructions|prompts|rules)",
            re.IGNORECASE,
        ),
        re.compile(r"system\s*:\s*you\s+are", re.IGNORECASE),
        re.compile(r"<\s*\|\s*im_start\s*\|\s*>", re.IGNORECASE),
        re.compile(r"<\s*\|\s*im_end\s*\|\s*>", re.IGNORECASE),
        re.compile(r"###\s*instruction", re.IGNORECASE),
        re.compile(r"###\s*system", re.IGNORECASE),
        re.compile(r"forget\s+(everything|all|previous)", re.IGNORECASE),
        re.compile(
            r"disregard\s+(previous|all)\s+(instructions|prompts)", re.IGNORECASE
        ),
        re.compile(r"you\s+are\s+now\s+a", re.IGNORECASE),
        re.compile(r"pretend\s+you\s+are", re.IGNORECASE),
        re.compile(r"act\s+as\s+if", re.IGNORECASE),
        re.compile(r"roleplay\s+as", re.IGNORECASE),
    ]

    # Patterns for potential code injection
    CODE_INJECTION_PATTERNS = [
        re.compile(r"<script[^>]*>", re.IGNORECASE),
        re.compile(r"javascript:", re.IGNORECASE),
        re.compile(r"on\w+\s*=", re.IGNORECASE),  # Event handlers like onclick=
        re.compile(r"eval\s*\(", re.IGNORECASE),
        re.compile(r"exec\s*\(", re.IGNORECASE),
        re.compile(r"__import__", re.IGNORECASE),
        re.compile(r"subprocess", re.IGNORECASE),
        re.compile(r"os\.system", re.IGNORECASE),
    ]

    def __init__(self, strict_mode: bool = False):
        """Initialize input validator.

        Args:
            strict_mode: If True, apply stricter validation rules
        """
        self.strict_mode = strict_mode

    def validate(self, user_input: str) -> ValidationResult:
        """Validate user input with security checks.

        Args:
            user_input: User input to validate

        Returns:
            ValidationResult with validation status and sanitized input
        """
        errors = []
        warnings = []

        # Check if input is empty
        if not user_input or not user_input.strip():
            errors.append("Input cannot be empty")
            return ValidationResult(
                valid=False,
                sanitized_input=None,
                errors=errors,
                warnings=warnings,
            )

        # Check length
        if len(user_input) < self.MIN_LENGTH:
            errors.append(f"Input must be at least {self.MIN_LENGTH} characters")

        if len(user_input) > self.MAX_LENGTH:
            errors.append(f"Input must not exceed {self.MAX_LENGTH} characters")

        # Check number of lines
        line_count = user_input.count("\n") + 1
        if line_count > self.MAX_LINES:
            if self.strict_mode:
                errors.append(f"Input must not exceed {self.MAX_LINES} lines")
            else:
                warnings.append(
                    f"Input has {line_count} lines (max recommended: {self.MAX_LINES})"
                )

        # Check for suspicious patterns (prompt injection attempts)
        for pattern in self.SUSPICIOUS_PATTERNS:
            if pattern.search(user_input):
                if self.strict_mode:
                    errors.append(
                        "Input contains suspicious patterns that may indicate prompt injection"
                    )
                    logger.warning(
                        "suspicious_pattern_detected",
                        pattern=pattern.pattern,
                        input_preview=user_input[:100],
                    )
                else:
                    warnings.append(
                        "Input contains patterns that may be misinterpreted"
                    )
                break

        # Check for code injection patterns
        for pattern in self.CODE_INJECTION_PATTERNS:
            if pattern.search(user_input):
                errors.append("Input contains potentially malicious code patterns")
                logger.warning(
                    "code_injection_pattern_detected",
                    pattern=pattern.pattern,
                    input_preview=user_input[:100],
                )
                break

        # Check for excessive special characters (potential obfuscation)
        special_char_count = sum(
            1 for c in user_input if not c.isalnum() and not c.isspace()
        )
        special_char_ratio = (
            special_char_count / len(user_input) if len(user_input) > 0 else 0
        )

        if special_char_ratio > 0.5:
            if self.strict_mode:
                errors.append("Input contains too many special characters")
            else:
                warnings.append("Input has a high ratio of special characters")

        # Check for repeated characters (potential DoS)
        if _REPEATED_CHARS_RE.search(user_input):
            errors.append("Input contains excessive character repetition")

        # If validation failed, return early
        if errors:
            logger.info(
                "input_validation_failed",
                errors=errors,
                warnings=warnings,
                input_length=len(user_input),
            )
            return ValidationResult(
                valid=False,
                sanitized_input=None,
                errors=errors,
                warnings=warnings,
            )

        # Sanitize input
        sanitized = self._sanitize(user_input)

        logger.debug(
            "input_validated",
            input_length=len(user_input),
            sanitized_length=len(sanitized),
            warnings_count=len(warnings),
        )

        return ValidationResult(
            valid=True,
            sanitized_input=sanitized,
            errors=errors,
            warnings=warnings,
        )

    def _sanitize(self, user_input: str) -> str:
        """Sanitize user input.

        Args:
            user_input: Input to sanitize

        Returns:
            Sanitized input
        """
        # Remove null bytes
        sanitized = user_input.replace("\x00", "")

        # Normalize whitespace (but preserve single newlines)
        sanitized = _WHITESPACE_RE.sub(" ", sanitized)
        sanitized = _MULTIPLE_NEWLINES_RE.sub("\n\n", sanitized)

        # Remove leading/trailing whitespace
        sanitized = sanitized.strip()

        # Remove any HTML tags (basic sanitization)
        sanitized = _HTML_TAGS_RE.sub("", sanitized)

        # Remove control characters except newlines and tabs
        sanitized = "".join(
            char
            for char in sanitized
            if char == "\n" or char == "\t" or (ord(char) >= 32 and ord(char) != 127)
        )

        return sanitized


class InputSanitizer:
    """Sanitizer for user input with configurable rules."""

    def __init__(
        self,
        remove_html: bool = True,
        normalize_whitespace: bool = True,
        remove_control_chars: bool = True,
    ):
        """Initialize input sanitizer.

        Args:
            remove_html: Remove HTML tags
            normalize_whitespace: Normalize whitespace
            remove_control_chars: Remove control characters
        """
        self.remove_html = remove_html
        self.normalize_whitespace = normalize_whitespace
        self.remove_control_chars = remove_control_chars

    def sanitize(self, user_input: str) -> str:
        """Sanitize user input.

        Args:
            user_input: Input to sanitize

        Returns:
            Sanitized input
        """
        if not user_input:
            return ""

        sanitized = user_input

        # Remove null bytes
        sanitized = sanitized.replace("\x00", "")

        # Remove HTML tags
        if self.remove_html:
            sanitized = _HTML_TAGS_RE.sub("", sanitized)

        # Normalize whitespace
        if self.normalize_whitespace:
            sanitized = _WHITESPACE_RE.sub(" ", sanitized)
            sanitized = _MULTIPLE_NEWLINES_RE.sub("\n\n", sanitized)

        # Remove control characters
        if self.remove_control_chars:
            sanitized = "".join(
                char
                for char in sanitized
                if char == "\n"
                or char == "\t"
                or (ord(char) >= 32 and ord(char) != 127)
            )

        # Trim
        sanitized = sanitized.strip()

        logger.debug(
            "input_sanitized",
            original_length=len(user_input),
            sanitized_length=len(sanitized),
        )

        return sanitized


# Convenience functions
def validate_query(query: str, strict_mode: bool = False) -> ValidationResult:
    """Validate a query string.

    Args:
        query: Query to validate
        strict_mode: Apply strict validation rules

    Returns:
        ValidationResult
    """
    validator = InputValidator(strict_mode=strict_mode)
    return validator.validate(query)


def sanitize_query(query: str) -> str:
    """Sanitize a query string.

    Args:
        query: Query to sanitize

    Returns:
        Sanitized query
    """
    sanitizer = InputSanitizer()
    return sanitizer.sanitize(query)

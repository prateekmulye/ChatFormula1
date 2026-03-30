"""Input validation and sanitization for security.

This module provides input validation and sanitization to prevent prompt injection,
XSS attacks, and other security vulnerabilities.
"""

import re
from typing import Optional

import structlog
from pydantic import BaseModel, Field, field_validator

logger = structlog.get_logger(__name__)


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
        r"ignore\s+(previous|above|all)\s+(instructions|prompts|rules)",
        r"system\s*:\s*you\s+are",
        r"<\s*\|\s*im_start\s*\|\s*>",
        r"<\s*\|\s*im_end\s*\|\s*>",
        r"###\s*instruction",
        r"###\s*system",
        r"forget\s+(everything|all|previous)",
        r"disregard\s+(previous|all)\s+(instructions|prompts)",
        r"you\s+are\s+now\s+a",
        r"pretend\s+you\s+are",
        r"act\s+as\s+if",
        r"roleplay\s+as",
    ]

    # Patterns for potential code injection
    CODE_INJECTION_PATTERNS = [
        r"<script[^>]*>",
        r"javascript:",
        r"on\w+\s*=",  # Event handlers like onclick=
        r"eval\s*\(",
        r"exec\s*\(",
        r"__import__",
        r"subprocess",
        r"os\.system",
    ]

    def __init__(self, strict_mode: bool = False):
        """Initialize input validator.

        Args:
            strict_mode: If True, apply stricter validation rules
        """
        self.strict_mode = strict_mode
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficiency."""
        self.suspicious_regex = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.SUSPICIOUS_PATTERNS
        ]
        self.code_injection_regex = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.CODE_INJECTION_PATTERNS
        ]

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
        for pattern in self.suspicious_regex:
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
        for pattern in self.code_injection_regex:
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
        if re.search(r"(.)\1{50,}", user_input):
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
        sanitized = re.sub(r"[ \t]+", " ", sanitized)
        sanitized = re.sub(r"\n{3,}", "\n\n", sanitized)

        # Remove leading/trailing whitespace
        sanitized = sanitized.strip()

        # Remove any HTML tags (basic sanitization)
        sanitized = re.sub(r"<[^>]+>", "", sanitized)

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
            sanitized = re.sub(r"<[^>]+>", "", sanitized)

        # Normalize whitespace
        if self.normalize_whitespace:
            sanitized = re.sub(r"[ \t]+", " ", sanitized)
            sanitized = re.sub(r"\n{3,}", "\n\n", sanitized)

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

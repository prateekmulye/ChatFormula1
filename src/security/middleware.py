"""Security middleware for FastAPI application.

This module provides middleware for input validation, rate limiting,
and request validation.
"""

from typing import Optional

import structlog
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.security.input_validation import InputValidator
from src.security.rate_limiting import RateLimitExceeded, get_rate_limiter

logger = structlog.get_logger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware for security features."""

    def __init__(
        self,
        app,
        enable_rate_limiting: bool = True,
        enable_input_validation: bool = True,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        strict_validation: bool = False,
    ):
        """Initialize security middleware.

        Args:
            app: FastAPI application
            enable_rate_limiting: Enable rate limiting
            enable_input_validation: Enable input validation
            requests_per_minute: Rate limit per minute
            requests_per_hour: Rate limit per hour
            strict_validation: Use strict input validation
        """
        super().__init__(app)
        self.enable_rate_limiting = enable_rate_limiting
        self.enable_input_validation = enable_input_validation
        self.strict_validation = strict_validation

        # Initialize rate limiter
        if enable_rate_limiting:
            self.rate_limiter = get_rate_limiter(
                requests_per_minute=requests_per_minute,
                requests_per_hour=requests_per_hour,
            )

        # Initialize input validator
        if enable_input_validation:
            self.input_validator = InputValidator(strict_mode=strict_validation)

        logger.info(
            "security_middleware_initialized",
            rate_limiting=enable_rate_limiting,
            input_validation=enable_input_validation,
            strict_validation=strict_validation,
        )

    async def dispatch(self, request: Request, call_next):
        """Process request through security checks.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response
        """
        # Skip security checks for health endpoints
        if request.url.path in ["/health", "/api/health"]:
            return await call_next(request)

        # Rate limiting
        if self.enable_rate_limiting:
            try:
                self.rate_limiter.check_rate_limit(request)
            except RateLimitExceeded as e:
                logger.warning(
                    "rate_limit_exceeded",
                    path=request.url.path,
                    client=request.client.host if request.client else "unknown",
                )
                return JSONResponse(
                    status_code=e.status_code,
                    content={"error": e.detail},
                    headers=e.headers,
                )

        # Continue with request
        response = await call_next(request)

        # Add rate limit headers
        if self.enable_rate_limiting:
            try:
                rate_info = self.rate_limiter.get_rate_limit_info(request)
                response.headers["X-RateLimit-Limit-Minute"] = str(
                    rate_info["limits"]["requests_per_minute"]
                )
                response.headers["X-RateLimit-Remaining-Minute"] = str(
                    rate_info["remaining"]["minute"]
                )
                response.headers["X-RateLimit-Limit-Hour"] = str(
                    rate_info["limits"]["requests_per_hour"]
                )
                response.headers["X-RateLimit-Remaining-Hour"] = str(
                    rate_info["remaining"]["hour"]
                )
            except Exception as e:
                logger.error("failed_to_add_rate_limit_headers", error=str(e))

        return response


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Middleware specifically for input validation on POST requests."""

    def __init__(
        self,
        app,
        strict_mode: bool = False,
        validate_paths: Optional[list[str]] = None,
    ):
        """Initialize input validation middleware.

        Args:
            app: FastAPI application
            strict_mode: Use strict validation
            validate_paths: Specific paths to validate (None = all POST requests)
        """
        super().__init__(app)
        self.strict_mode = strict_mode
        self.validate_paths = validate_paths
        self.validator = InputValidator(strict_mode=strict_mode)

        logger.info(
            "input_validation_middleware_initialized",
            strict_mode=strict_mode,
            validate_paths=validate_paths,
        )

    async def dispatch(self, request: Request, call_next):
        """Validate input on POST requests.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response
        """
        # Only validate POST requests
        if request.method != "POST":
            return await call_next(request)

        # Check if path should be validated
        if self.validate_paths and request.url.path not in self.validate_paths:
            return await call_next(request)

        # Skip validation for certain endpoints
        skip_paths = ["/api/admin/ingest", "/api/admin/feedback"]
        if request.url.path in skip_paths:
            return await call_next(request)

        # Try to read and validate request body
        try:
            # Read body
            body = await request.body()

            # Parse JSON if content-type is JSON
            if "application/json" in request.headers.get("content-type", ""):
                import json

                try:
                    data = json.loads(body)

                    # Validate message field if present
                    if isinstance(data, dict) and "message" in data:
                        message = data["message"]
                        if isinstance(message, str):
                            validation_result = self.validator.validate(message)

                            if not validation_result.valid:
                                logger.warning(
                                    "input_validation_failed",
                                    path=request.url.path,
                                    errors=validation_result.errors,
                                )
                                return JSONResponse(
                                    status_code=status.HTTP_400_BAD_REQUEST,
                                    content={
                                        "error": "Invalid input",
                                        "details": validation_result.errors,
                                        "warnings": validation_result.warnings,
                                    },
                                )

                            # Log warnings if any
                            if validation_result.warnings:
                                logger.info(
                                    "input_validation_warnings",
                                    path=request.url.path,
                                    warnings=validation_result.warnings,
                                )

                except json.JSONDecodeError:
                    pass  # Let the endpoint handle invalid JSON

            # Reconstruct request with original body
            async def receive():
                return {"type": "http.request", "body": body}

            request._receive = receive

        except Exception as e:
            logger.error(
                "input_validation_middleware_error",
                error=str(e),
                exc_info=True,
            )

        return await call_next(request)

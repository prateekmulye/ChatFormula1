"""Authentication and authorization for API endpoints.

This module provides authentication mechanisms including API key validation
and optional JWT token support.
"""

import secrets
from datetime import datetime, timedelta

import bcrypt
import structlog
from fastapi import HTTPException, Request, Security, status
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader, HTTPBearer
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

logger = structlog.get_logger(__name__)


class APIKey(BaseModel):
    """API key model."""

    key_id: str = Field(..., description="Unique key identifier")
    key_hash: str = Field(..., description="Hashed API key")
    name: str = Field(..., description="Key name/description")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = Field(None, description="Expiration date")
    is_active: bool = Field(default=True, description="Whether key is active")
    scopes: list[str] = Field(default_factory=list, description="Allowed scopes")
    rate_limit_multiplier: float = Field(
        default=1.0,
        description="Rate limit multiplier (1.0 = normal, 2.0 = double)",
    )


class APIKeyManager:
    """Manager for API keys."""

    def __init__(self) -> None:
        """Initialize API key manager."""
        # In production, store keys in a database
        self.keys: dict[str, APIKey] = {}
        logger.info("api_key_manager_initialized")

    async def generate_key(
        self,
        name: str,
        scopes: list[str] | None = None,
        expires_in_days: int | None = None,
        rate_limit_multiplier: float = 1.0,
    ) -> tuple[str, APIKey]:
        """Generate a new API key.

        Args:
            name: Key name/description
            scopes: Allowed scopes
            expires_in_days: Days until expiration (None = no expiration)
            rate_limit_multiplier: Rate limit multiplier

        Returns:
            Tuple of (raw_key, api_key_model)
        """
        # Generate key ID and secret using token_hex to avoid underscores
        key_id = secrets.token_hex(8)  # 16 chars
        secret = secrets.token_hex(16)  # 32 chars

        # Generate random key
        raw_key = f"f1s_{key_id}_{secret}"

        # Hash the secret for storage
        key_hash = await self._hash_key(secret)

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        # Create API key model
        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            expires_at=expires_at,
            scopes=scopes or [],
            rate_limit_multiplier=rate_limit_multiplier,
        )

        # Store key by key_id for O(1) retrieval
        self.keys[key_id] = api_key

        logger.info(
            "api_key_generated",
            key_id=key_id,
            name=name,
            scopes=scopes,
            expires_at=expires_at,
        )

        return raw_key, api_key

    async def validate_key(self, raw_key: str) -> APIKey | None:
        """Validate an API key.

        Args:
            raw_key: Raw API key to validate

        Returns:
            APIKey model if valid, None otherwise
        """
        # Parse raw key
        parts = raw_key.split("_")
        if len(parts) != 3 or parts[0] != "f1s":
            logger.warning("api_key_invalid_format")
            return None

        _, key_id, secret = parts

        # Look up key by key_id
        api_key = self.keys.get(key_id)

        if not api_key:
            logger.warning("api_key_not_found")
            return None

        # Verify secret matches hash
        is_valid = await run_in_threadpool(
            bcrypt.checkpw, secret.encode(), api_key.key_hash.encode()
        )

        if not is_valid:
            logger.warning("api_key_invalid_secret")
            return None

        # Check if key is active
        if not api_key.is_active:
            logger.warning("api_key_inactive", key_id=api_key.key_id)
            return None

        # Check if key is expired
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            logger.warning("api_key_expired", key_id=api_key.key_id)
            return None

        logger.debug("api_key_validated", key_id=api_key.key_id)
        return api_key

    def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key.

        Args:
            key_id: Key ID to revoke

        Returns:
            True if key was revoked, False if not found
        """
        api_key = self.keys.get(key_id)
        if api_key:
            api_key.is_active = False
            logger.info("api_key_revoked", key_id=key_id)
            return True

        logger.warning("api_key_not_found_for_revocation", key_id=key_id)
        return False

    async def rotate_key(self, key_id: str) -> tuple[str, APIKey] | None:
        """Rotate an API key (generate new key with same settings).

        Args:
            key_id: Key ID to rotate

        Returns:
            Tuple of (new_raw_key, new_api_key) if successful, None otherwise
        """
        # Find existing key
        old_key = self.keys.get(key_id)

        if not old_key:
            logger.warning("api_key_not_found_for_rotation", key_id=key_id)
            return None

        # Generate new key with same settings
        new_raw_key, new_api_key = await self.generate_key(
            name=f"{old_key.name} (rotated)",
            scopes=old_key.scopes,
            expires_in_days=None,  # Reset expiration
            rate_limit_multiplier=old_key.rate_limit_multiplier,
        )

        # Deactivate old key
        old_key.is_active = False

        logger.info(
            "api_key_rotated",
            old_key_id=key_id,
            new_key_id=new_api_key.key_id,
        )

        return new_raw_key, new_api_key

    def list_keys(self, include_inactive: bool = False) -> list[APIKey]:
        """List all API keys.

        Args:
            include_inactive: Include inactive keys

        Returns:
            List of API keys
        """
        keys = list(self.keys.values())

        if not include_inactive:
            keys = [key for key in keys if key.is_active]

        return keys

    async def _hash_key(self, secret: str) -> str:
        """Hash an API key secret for storage using bcrypt.

        Args:
            secret: API key secret

        Returns:
            Hashed key
        """

        def hash_secret():
            return bcrypt.hashpw(secret.encode(), bcrypt.gensalt()).decode()

        return await run_in_threadpool(hash_secret)


# Global API key manager
_api_key_manager: APIKeyManager | None = None


def get_api_key_manager() -> APIKeyManager:
    """Get or create global API key manager.

    Returns:
        APIKeyManager instance
    """
    global _api_key_manager

    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()

    return _api_key_manager


# FastAPI security schemes
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_auth = HTTPBearer(auto_error=False)


async def verify_api_key(
    api_key: str | None = Security(api_key_header),
) -> APIKey | None:
    """Verify API key from header.

    Args:
        api_key: API key from header

    Returns:
        APIKey model if valid

    Raises:
        HTTPException: If API key is invalid or missing
    """
    if not api_key:
        logger.warning("api_key_missing")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required. Provide it in the X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Validate key
    manager = get_api_key_manager()
    validated_key = await manager.validate_key(api_key)

    if not validated_key:
        logger.warning("api_key_invalid")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return validated_key


async def verify_api_key_optional(
    api_key: str | None = Security(api_key_header),
) -> APIKey | None:
    """Verify API key from header (optional).

    Args:
        api_key: API key from header

    Returns:
        APIKey model if valid, None if not provided
    """
    if not api_key:
        return None

    # Validate key
    manager = get_api_key_manager()
    return await manager.validate_key(api_key)


def require_scope(required_scope: str):
    """Dependency to require a specific scope.

    Args:
        required_scope: Required scope

    Returns:
        Dependency function
    """

    async def scope_checker(api_key: APIKey = Security(verify_api_key)) -> APIKey:
        """Check if API key has required scope.

        Args:
            api_key: Validated API key

        Returns:
            APIKey if scope is present

        Raises:
            HTTPException: If scope is missing
        """
        if required_scope not in api_key.scopes and "*" not in api_key.scopes:
            logger.warning(
                "insufficient_scope",
                key_id=api_key.key_id,
                required_scope=required_scope,
                available_scopes=api_key.scopes,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required scope: {required_scope}",
            )

        return api_key

    return scope_checker


class AuthenticationMiddleware:
    """Middleware for authentication."""

    def __init__(
        self,
        app,
        require_auth: bool = False,
        public_paths: list[str] | None = None,
    ) -> None:
        """Initialize authentication middleware.

        Args:
            app: FastAPI application
            require_auth: Require authentication for all endpoints
            public_paths: Paths that don't require authentication
        """
        self.app = app
        self.require_auth = require_auth
        self.public_paths = public_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]

        logger.info(
            "authentication_middleware_initialized",
            require_auth=require_auth,
            public_paths=public_paths,
        )

    async def __call__(self, request: Request, call_next):
        """Process request through authentication.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response
        """
        # Check if path is public
        if request.url.path in self.public_paths:
            return await call_next(request)

        # If authentication is not required, continue
        if not self.require_auth:
            # Try to get API key for rate limit adjustment
            api_key = request.headers.get("X-API-Key")
            if api_key:
                manager = get_api_key_manager()
                validated_key = await manager.validate_key(api_key)
                if validated_key:
                    # Store in request state for rate limiter
                    request.state.api_key = validated_key
                    request.state.user_id = validated_key.key_id

            return await call_next(request)

        # Require authentication
        api_key = request.headers.get("X-API-Key")

        if not api_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "API key is required"},
                headers={"WWW-Authenticate": "ApiKey"},
            )

        # Validate key
        manager = get_api_key_manager()
        validated_key = await manager.validate_key(api_key)

        if not validated_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "Invalid or expired API key"},
                headers={"WWW-Authenticate": "ApiKey"},
            )

        # Store in request state
        request.state.api_key = validated_key
        request.state.user_id = validated_key.key_id

        return await call_next(request)

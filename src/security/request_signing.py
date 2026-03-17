"""Request signing for sensitive operations.

This module provides request signing and verification to ensure request integrity
and prevent tampering.
"""

import hashlib
import hmac
import time
from typing import Optional

import structlog
from fastapi import HTTPException, Request, status

logger = structlog.get_logger(__name__)


class RequestSigner:
    """Request signer for sensitive operations."""

    def __init__(self, secret_key: str, max_age_seconds: int = 300):
        """Initialize request signer.

        Args:
            secret_key: Secret key for signing
            max_age_seconds: Maximum age of signed requests in seconds
        """
        self.secret_key = secret_key.encode()
        self.max_age_seconds = max_age_seconds
        logger.info(
            "request_signer_initialized",
            max_age_seconds=max_age_seconds,
        )

    def sign_request(
        self,
        method: str,
        path: str,
        body: Optional[str] = None,
        timestamp: Optional[int] = None,
    ) -> str:
        """Sign a request.

        Args:
            method: HTTP method
            path: Request path
            body: Request body (optional)
            timestamp: Unix timestamp (defaults to current time)

        Returns:
            Signature string
        """
        if timestamp is None:
            timestamp = int(time.time())

        # Build string to sign
        parts = [
            str(timestamp),
            method.upper(),
            path,
        ]

        if body:
            # Hash body for large payloads
            body_hash = hashlib.sha256(body.encode()).hexdigest()
            parts.append(body_hash)

        string_to_sign = "\n".join(parts)

        # Generate signature
        signature = hmac.new(
            self.secret_key,
            string_to_sign.encode(),
            hashlib.sha256,
        ).hexdigest()

        logger.debug(
            "request_signed",
            method=method,
            path=path,
            timestamp=timestamp,
        )

        return f"{timestamp}.{signature}"

    def verify_signature(
        self,
        signature: str,
        method: str,
        path: str,
        body: Optional[str] = None,
    ) -> bool:
        """Verify a request signature.

        Args:
            signature: Signature to verify
            method: HTTP method
            path: Request path
            body: Request body (optional)

        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Parse signature
            parts = signature.split(".", 1)
            if len(parts) != 2:
                logger.warning("invalid_signature_format")
                return False

            timestamp_str, provided_sig = parts
            timestamp = int(timestamp_str)

            # Check timestamp age
            current_time = int(time.time())
            age = current_time - timestamp

            if age > self.max_age_seconds:
                logger.warning(
                    "signature_expired",
                    age_seconds=age,
                    max_age_seconds=self.max_age_seconds,
                )
                return False

            if age < -60:  # Allow 1 minute clock skew
                logger.warning("signature_from_future", age_seconds=age)
                return False

            # Compute expected signature
            expected_sig = self.sign_request(method, path, body, timestamp)
            expected_sig_value = expected_sig.split(".", 1)[1]

            # Compare signatures (constant time)
            is_valid = hmac.compare_digest(provided_sig, expected_sig_value)

            if not is_valid:
                logger.warning("signature_mismatch")
            else:
                logger.debug("signature_verified")

            return is_valid

        except Exception as e:
            logger.error(
                "signature_verification_error",
                error=str(e),
                exc_info=True,
            )
            return False

    async def verify_request(self, request: Request) -> None:
        """Verify a FastAPI request signature.

        Args:
            request: FastAPI request

        Raises:
            HTTPException: If signature is missing or invalid
        """
        # Get signature from header
        signature = request.headers.get("X-Signature")

        if not signature:
            logger.warning("signature_missing", path=request.url.path)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Request signature is required",
                headers={"WWW-Authenticate": "Signature"},
            )

        # Read body
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            body_bytes = await request.body()
            if body_bytes:
                body = body_bytes.decode()

        # Verify signature
        is_valid = self.verify_signature(
            signature=signature,
            method=request.method,
            path=request.url.path,
            body=body,
        )

        if not is_valid:
            logger.warning(
                "invalid_request_signature",
                path=request.url.path,
                method=request.method,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid request signature",
                headers={"WWW-Authenticate": "Signature"},
            )


# Global request signer
_request_signer: Optional[RequestSigner] = None


def get_request_signer(secret_key: Optional[str] = None) -> RequestSigner:
    """Get or create global request signer.

    Args:
        secret_key: Secret key for signing (required on first call)

    Returns:
        RequestSigner instance

    Raises:
        ValueError: If secret_key is not provided on first call
    """
    global _request_signer

    if _request_signer is None:
        if not secret_key:
            raise ValueError("secret_key is required to initialize request signer")

        _request_signer = RequestSigner(secret_key=secret_key)

    return _request_signer


def require_signed_request():
    """Dependency to require signed requests.

    Returns:
        Dependency function
    """

    async def verify_signature(request: Request) -> None:
        """Verify request signature.

        Args:
            request: FastAPI request

        Raises:
            HTTPException: If signature is invalid
        """
        signer = get_request_signer()
        await signer.verify_request(request)

    return verify_signature

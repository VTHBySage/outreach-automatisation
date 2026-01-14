"""Webhook security utilities for signature verification."""

import hashlib
import hmac
from typing import Callable

from fastapi import HTTPException, Request, status

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def verify_webhook_signature(
    request: Request,
    secret: str,
    signature_header: str = "X-Webhook-Signature",
    hash_algorithm: Callable = hashlib.sha256,
) -> bytes:
    """
    Verify webhook signature using HMAC.

    Args:
        request: FastAPI request object
        secret: Webhook secret for HMAC
        signature_header: Header name containing the signature
        hash_algorithm: Hash algorithm to use (default SHA256)

    Returns:
        Raw request body (already read for verification)

    Raises:
        HTTPException: If signature is missing or invalid
    """
    # Get signature from header
    signature = request.headers.get(signature_header)

    # If no secret configured, skip verification (development mode)
    if not secret:
        logger.warning(
            "webhook_signature_verification_skipped",
            reason="no_secret_configured",
            header=signature_header,
        )
        return await request.body()

    if not signature:
        logger.warning(
            "webhook_signature_missing",
            header=signature_header,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing webhook signature",
        )

    # Get raw body for HMAC calculation
    body = await request.body()

    # Calculate expected signature
    expected_signature = hmac.new(
        key=secret.encode(),
        msg=body,
        digestmod=hash_algorithm,
    ).hexdigest()

    # Compare signatures (constant-time comparison)
    if not hmac.compare_digest(signature, expected_signature):
        logger.warning(
            "webhook_signature_invalid",
            received=signature[:20] + "...",  # Log partial for debugging
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    logger.debug("webhook_signature_verified")
    return body


async def verify_smartlead_signature(request: Request) -> bytes:
    """Verify SmartLead webhook signature."""
    secret = settings.smartlead_webhook_secret.get_secret_value()
    return await verify_webhook_signature(
        request=request,
        secret=secret,
        signature_header="X-Smartlead-Signature",
    )


async def verify_connectsafely_signature(request: Request) -> bytes:
    """Verify ConnectSafely webhook signature."""
    secret = settings.connectsafely_webhook_secret.get_secret_value()
    return await verify_webhook_signature(
        request=request,
        secret=secret,
        signature_header="X-ConnectSafely-Signature",
    )

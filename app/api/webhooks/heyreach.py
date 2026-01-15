"""HeyReach webhook handler.

Performance requirement: < 200ms response time.
Strategy: Fast acknowledgment, offload processing to Celery.
"""

import hashlib
import hmac
import time
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.api.webhooks.schemas import HeyReachWebhookPayload, WebhookResponse
from app.config import settings
from app.core.constants import WebhookSource
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


def verify_heyreach_signature(request_body: bytes, signature: str | None) -> bool:
    """Verify HeyReach webhook signature."""
    if not signature:
        return False

    secret = settings.heyreach_webhook_secret.get_secret_value()
    if not secret:
        # If no secret configured, skip verification (development mode)
        logger.warning("heyreach_webhook_secret_not_configured")
        return True

    expected_signature = hmac.new(
        secret.encode(),
        request_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)


@router.post("", response_model=WebhookResponse)
async def handle_heyreach_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> WebhookResponse:
    """
    Handle HeyReach webhook events.

    Fast acknowledgment pattern:
    1. Verify signature
    2. Validate payload
    3. Log webhook receipt
    4. Queue for async processing
    5. Return 200 OK immediately
    """
    start_time = time.time()
    webhook_id = str(uuid4())

    # Read raw body
    raw_body = await request.body()

    # Verify signature
    signature = request.headers.get("X-HeyReach-Signature")
    if not verify_heyreach_signature(raw_body, signature):
        logger.warning(
            "heyreach_webhook_invalid_signature",
            webhook_id=webhook_id,
        )
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse payload
    try:
        payload = HeyReachWebhookPayload.model_validate_json(raw_body)
    except Exception as e:
        logger.error(
            "heyreach_webhook_invalid_payload",
            webhook_id=webhook_id,
            error=str(e),
        )
        raise HTTPException(status_code=400, detail="Invalid payload")

    # Log webhook receipt
    logger.info(
        "heyreach_webhook_received",
        webhook_id=webhook_id,
        event_type=payload.event_type,
        lead_id=payload.lead_id,
        campaign_id=payload.campaign_id,
    )

    # Queue async processing
    background_tasks.add_task(
        _queue_webhook_processing,
        webhook_id=webhook_id,
        payload=payload,
        headers=dict(request.headers),
        received_at=datetime.utcnow(),
    )

    # Log response time
    elapsed_ms = (time.time() - start_time) * 1000
    logger.info(
        "heyreach_webhook_acknowledged",
        webhook_id=webhook_id,
        elapsed_ms=round(elapsed_ms, 2),
    )

    return WebhookResponse(
        status="received",
        message="Webhook queued for processing",
        webhook_id=webhook_id,
    )


async def _queue_webhook_processing(
    webhook_id: str,
    payload: HeyReachWebhookPayload,
    headers: dict,
    received_at: datetime,
) -> None:
    """Queue webhook for Celery processing."""
    try:
        from app.workers.webhook_tasks import process_heyreach_webhook

        process_heyreach_webhook.delay(
            webhook_id=webhook_id,
            payload=payload.model_dump(mode="json"),
            source=WebhookSource.HEYREACH.value,
            received_at=received_at.isoformat(),
        )
    except Exception as e:
        logger.error(
            "heyreach_webhook_queue_failed",
            webhook_id=webhook_id,
            error=str(e),
        )

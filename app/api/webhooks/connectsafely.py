"""ConnectSafely (LinkedIn) webhook handler.

Performance requirement: < 200ms response time.
Strategy: Fast acknowledgment, offload processing to Celery.
"""

import json
import time
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, Request

from app.api.webhooks.schemas import ConnectSafelyWebhookPayload, WebhookResponse
from app.api.webhooks.security import verify_connectsafely_signature
from app.core.constants import WebhookSource
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("", response_model=WebhookResponse)
async def handle_connectsafely_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    raw_body: bytes = Depends(verify_connectsafely_signature),
) -> WebhookResponse:
    """
    Handle ConnectSafely webhook events.

    Events include:
    - Connection request accepted/rejected
    - LinkedIn DM reply received
    - Profile engagement detected

    Signature verification is performed by the verify_connectsafely_signature dependency.
    """
    start_time = time.time()
    webhook_id = str(uuid4())

    # Parse validated body into payload model
    payload = ConnectSafelyWebhookPayload.model_validate_json(raw_body)

    # Log webhook receipt
    logger.info(
        "connectsafely_webhook_received",
        webhook_id=webhook_id,
        event_type=payload.event_type,
        profile_url=payload.profile_url,
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
        "connectsafely_webhook_acknowledged",
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
    payload: ConnectSafelyWebhookPayload,
    headers: dict,
    received_at: datetime,
) -> None:
    """Queue webhook for Celery processing."""
    try:
        from app.workers.webhook_tasks import process_connectsafely_webhook

        process_connectsafely_webhook.delay(
            webhook_id=webhook_id,
            payload=payload.model_dump(),
            source=WebhookSource.CONNECTSAFELY.value,
            received_at=received_at.isoformat(),
        )
    except Exception as e:
        logger.error(
            "connectsafely_webhook_queue_failed",
            webhook_id=webhook_id,
            error=str(e),
        )

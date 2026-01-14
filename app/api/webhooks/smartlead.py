"""SmartLead webhook handler.

Performance requirement: < 200ms response time.
Strategy: Fast acknowledgment, offload processing to Celery.
"""

import time
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, Request

from app.api.webhooks.schemas import SmartLeadWebhookPayload, WebhookResponse
from app.api.webhooks.security import verify_smartlead_signature
from app.core.constants import WebhookSource
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("", response_model=WebhookResponse)
async def handle_smartlead_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    raw_body: bytes = Depends(verify_smartlead_signature),
) -> WebhookResponse:
    """
    Handle SmartLead webhook events.

    Fast acknowledgment pattern:
    1. Verify signature (via dependency)
    2. Validate payload (done by Pydantic)
    3. Log webhook receipt
    4. Queue for async processing
    5. Return 200 OK immediately
    """
    start_time = time.time()
    webhook_id = str(uuid4())

    # Parse validated body into payload model
    payload = SmartLeadWebhookPayload.model_validate_json(raw_body)

    # Log webhook receipt
    logger.info(
        "smartlead_webhook_received",
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
        "smartlead_webhook_acknowledged",
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
    payload: SmartLeadWebhookPayload,
    headers: dict,
    received_at: datetime,
) -> None:
    """Queue webhook for Celery processing."""
    try:
        from app.workers.webhook_tasks import process_smartlead_webhook

        process_smartlead_webhook.delay(
            webhook_id=webhook_id,
            payload=payload.model_dump(),
            source=WebhookSource.SMARTLEAD.value,
            received_at=received_at.isoformat(),
        )
    except Exception as e:
        logger.error(
            "smartlead_webhook_queue_failed",
            webhook_id=webhook_id,
            error=str(e),
        )

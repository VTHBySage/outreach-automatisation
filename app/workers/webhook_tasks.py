"""Webhook processing tasks."""

from datetime import datetime
from uuid import uuid4

from celery import shared_task
from sqlalchemy.exc import IntegrityError

from app.core.constants import WebhookSource
from app.core.logging import get_logger
from app.core.utils import run_async
from app.db.session import async_session_factory

logger = get_logger(__name__)


async def _process_smartlead_webhook_async(
    webhook_id: str,
    payload: dict,
    source: str,
    received_at_str: str,
) -> dict:
    """
    Async implementation of SmartLead webhook processing.

    SmartLead API payload fields (https://api.smartlead.ai/reference/email-reply-webhooks):
    - sl_lead_email: Lead's email address
    - sl_email_lead_id: SmartLead internal lead ID
    - campaign_id: Campaign identifier
    - preview_text: Email reply content preview
    - subject: Email subject
    - time_replied: When reply was received
    - message_id: Unique email message ID
    - to_name: Recipient name
    - leadCorrespondence: Enhanced tracking object
    """
    from app.db.models.webhook_log import WebhookLog
    from app.db.repositories.contact import ContactRepository
    from app.db.repositories.email_reply import EmailReplyRepository
    from app.workers.categorization_tasks import categorize_email_reply

    received_at = datetime.fromisoformat(received_at_str)

    async with async_session_factory() as session:
        try:
            # Extract data from SmartLead payload (using correct field names with fallbacks)
            # SmartLead uses sl_lead_email, but support legacy 'email' field
            email = payload.get("sl_lead_email") or payload.get("email")

            # SmartLead uses sl_email_lead_id, but support legacy 'lead_id' field
            # Also get message_id for duplicate detection (more reliable than lead_id)
            lead_id = payload.get("sl_email_lead_id") or payload.get("lead_id")
            message_id = payload.get("message_id")

            # Use message_id for duplicate detection, fall back to lead_id, then generate UUID
            external_id = message_id or lead_id or str(uuid4())

            # Campaign ID is the same
            campaign_id = payload.get("campaign_id")

            # SmartLead uses preview_text for reply content
            reply_text = (
                payload.get("preview_text")
                or payload.get("reply_text")
                or ""
            )

            # SmartLead doesn't send HTML by default
            reply_html = payload.get("reply_html")

            # Subject is the same
            subject = payload.get("subject")

            # SmartLead uses time_replied for timestamp
            reply_timestamp = payload.get("time_replied") or payload.get("event_timestamp")
            if reply_timestamp and isinstance(reply_timestamp, str):
                try:
                    received_at = datetime.fromisoformat(reply_timestamp.replace("Z", "+00:00"))
                except ValueError:
                    pass  # Keep original received_at

            # SmartLead uses to_name for recipient name
            # Safe parsing: check for non-empty string before splitting
            to_name = payload.get("to_name", "") or ""
            to_name_parts = to_name.split() if to_name.strip() else []
            first_name = payload.get("first_name") or (to_name_parts[0] if to_name_parts else None)
            last_name = payload.get("last_name") or (
                " ".join(to_name_parts[1:]) if len(to_name_parts) > 1 else None
            )

            # SmartLead uses message_id for thread tracking
            thread_id = payload.get("message_id") or payload.get("thread_id")

            # Enhanced tracking from leadCorrespondence
            lead_correspondence = payload.get("leadCorrespondence", {})
            if lead_correspondence:
                # Use actual responder email if different from target
                actual_responder = lead_correspondence.get("replyReceivedFrom")
                if actual_responder and actual_responder != email:
                    logger.info(
                        "reply_from_different_email",
                        webhook_id=webhook_id,
                        target_email=email,
                        actual_responder=actual_responder,
                        domain_match=lead_correspondence.get("repliedCompanyDomain"),
                    )

            if not email:
                logger.warning(
                    "smartlead_webhook_missing_email",
                    webhook_id=webhook_id,
                    payload_keys=list(payload.keys()),
                )
                # Log webhook even when skipping (for audit trail)
                webhook_log = WebhookLog(
                    source=WebhookSource.SMARTLEAD.value,
                    endpoint="/webhook/smartlead",
                    method="POST",
                    headers={},
                    payload=payload,
                    processed=False,
                    response_status=200,
                    received_at=received_at,
                )
                session.add(webhook_log)
                await session.commit()

                return {
                    "status": "skipped",
                    "reason": "missing_email",
                    "webhook_id": webhook_id,
                }

            # Initialize repositories
            contact_repo = ContactRepository(session)
            reply_repo = EmailReplyRepository(session)

            # 1. Find or create contact
            contact, created = await contact_repo.get_or_create_by_email(
                email=email,
                first_name=first_name,
                last_name=last_name,
                company_name=payload.get("company_name"),
                smartlead_lead_id=lead_id,
            )

            logger.info(
                "contact_processed",
                webhook_id=webhook_id,
                contact_id=str(contact.id),
                created=created,
            )

            # 2. Check for duplicate reply (using external_id which prioritizes message_id)
            existing_reply = await reply_repo.get_by_external_id(
                source=WebhookSource.SMARTLEAD.value,
                external_id=external_id,
            )
            if existing_reply:
                logger.info(
                    "duplicate_reply_skipped",
                    webhook_id=webhook_id,
                    external_id=external_id,
                )
                return {
                    "status": "skipped",
                    "reason": "duplicate",
                    "webhook_id": webhook_id,
                }

            # 3. Create email reply record (with race condition protection)
            try:
                email_reply = await reply_repo.create_from_webhook(
                    contact_id=contact.id,
                    source=WebhookSource.SMARTLEAD.value,
                    external_id=external_id,
                    body_text=reply_text,
                    subject=subject,
                    body_html=reply_html,
                    received_at=received_at,
                    campaign_external_id=campaign_id,
                )
                await session.flush()
            except IntegrityError:
                # Race condition: another process created this reply between our check and create
                await session.rollback()
                logger.info(
                    "duplicate_reply_race_condition",
                    webhook_id=webhook_id,
                    external_id=external_id,
                )
                return {
                    "status": "skipped",
                    "reason": "duplicate",
                    "webhook_id": webhook_id,
                }

            logger.info(
                "email_reply_created",
                webhook_id=webhook_id,
                reply_id=str(email_reply.id),
                contact_id=str(contact.id),
            )

            # 4. Update contact last response
            contact.last_response_at = received_at
            await session.flush()

            # 5. Log webhook
            webhook_log = WebhookLog(
                source=WebhookSource.SMARTLEAD.value,
                endpoint="/webhook/smartlead",
                method="POST",
                headers={},
                payload=payload,
                processed=True,
                response_status=200,
                received_at=received_at,
            )
            session.add(webhook_log)

            # 6. Commit transaction
            await session.commit()

            # 7. Queue categorization task (after commit to ensure data is persisted)
            categorize_email_reply.delay(
                reply_id=str(email_reply.id),
                subject=subject or "",
                body=reply_text,
                context=None,
            )

            logger.info(
                "categorization_queued",
                webhook_id=webhook_id,
                reply_id=str(email_reply.id),
            )

            return {
                "status": "processed",
                "webhook_id": webhook_id,
                "contact_id": str(contact.id),
                "reply_id": str(email_reply.id),
                "contact_created": created,
                "processed_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            await session.rollback()
            raise e


def _record_email_engagement_metrics(event_type: str | None, campaign_id: str | None) -> None:
    """Record email engagement metrics based on event type."""
    from app.core.metrics import (
        EMAIL_BOUNCES,
        EMAIL_CLICKS,
        EMAIL_OPENS,
        EMAIL_REPLIES,
        EMAIL_UNSUBSCRIBES,
    )

    campaign = str(campaign_id) if campaign_id else "unknown"

    if event_type == "EMAIL_OPENED":
        EMAIL_OPENS.labels(campaign_id=campaign).inc()
    elif event_type == "EMAIL_CLICKED":
        EMAIL_CLICKS.labels(campaign_id=campaign).inc()
    elif event_type == "EMAIL_REPLY":
        EMAIL_REPLIES.labels(campaign_id=campaign).inc()
    elif event_type == "EMAIL_BOUNCED":
        EMAIL_BOUNCES.labels(campaign_id=campaign, bounce_type="unknown").inc()
    elif event_type == "HARD_BOUNCE":
        EMAIL_BOUNCES.labels(campaign_id=campaign, bounce_type="hard").inc()
    elif event_type == "SOFT_BOUNCE":
        EMAIL_BOUNCES.labels(campaign_id=campaign, bounce_type="soft").inc()
    elif event_type == "EMAIL_UNSUBSCRIBED":
        EMAIL_UNSUBSCRIBES.labels(campaign_id=campaign).inc()


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    rate_limit="100/m",  # Limit to 100 webhooks per minute
)
def process_smartlead_webhook(
    self,
    webhook_id: str,
    payload: dict,
    source: str,
    received_at: str,
) -> dict:
    """
    Process SmartLead webhook asynchronously.

    Flow:
    1. Parse payload
    2. Record email engagement metrics
    3. Find or create contact
    4. Create email reply record
    5. Trigger categorization task
    """
    try:
        event_type = payload.get("event_type")
        campaign_id = payload.get("campaign_id")

        logger.info(
            "processing_smartlead_webhook",
            webhook_id=webhook_id,
            event_type=event_type,
        )

        # Record engagement metrics for all event types
        _record_email_engagement_metrics(event_type, campaign_id)

        # Only process replies through full async flow
        # Other events (opens, clicks, bounces) are tracked in metrics only
        if event_type not in ("EMAIL_REPLY", None):
            logger.info(
                "engagement_event_recorded",
                webhook_id=webhook_id,
                event_type=event_type,
                campaign_id=campaign_id,
            )
            return {
                "status": "recorded",
                "webhook_id": webhook_id,
                "event_type": event_type,
                "campaign_id": str(campaign_id) if campaign_id else None,
            }

        # Run async code in sync context for replies
        result = run_async(
            _process_smartlead_webhook_async(
                webhook_id=webhook_id,
                payload=payload,
                source=source,
                received_at_str=received_at,
            )
        )

        return result

    except Exception as e:
        logger.error(
            "smartlead_webhook_processing_failed",
            webhook_id=webhook_id,
            error=str(e),
        )
        raise self.retry(exc=e)


async def _process_connectsafely_webhook_async(
    webhook_id: str,
    payload: dict,
    source: str,
    received_at_str: str,
) -> dict:
    """Async implementation of ConnectSafely webhook processing."""
    from app.db.models.webhook_log import WebhookLog
    from app.db.repositories.contact import ContactRepository
    from app.db.repositories.email_reply import EmailReplyRepository
    from app.workers.categorization_tasks import categorize_email_reply

    received_at = datetime.fromisoformat(received_at_str)

    async with async_session_factory() as session:
        try:
            event_type = payload.get("event_type")
            profile_url = payload.get("profile_url")
            email = payload.get("email")
            message_text = payload.get("message_text")
            message_id = payload.get("message_id") or str(uuid4())

            contact_repo = ContactRepository(session)
            reply_repo = EmailReplyRepository(session)

            # Try to find contact by email
            contact = None
            if email:
                contact = await contact_repo.get_by_email(email)

            # Log webhook
            webhook_log = WebhookLog(
                source=WebhookSource.CONNECTSAFELY.value,
                endpoint="/webhook/connectsafely",
                method="POST",
                headers={},
                payload=payload,
                processed=True,
                response_status=200,
                received_at=received_at,
            )
            session.add(webhook_log)

            reply_id = None

            # Handle different event types
            if event_type == "connection_accepted" and contact:
                contact.linkedin_url = profile_url
                logger.info(
                    "linkedin_connection_updated",
                    webhook_id=webhook_id,
                    contact_id=str(contact.id),
                )

            # Handle LinkedIn DM replies - categorize them like email replies
            elif event_type == "message_received" and message_text and contact:
                # Check for duplicate
                existing_reply = await reply_repo.get_by_external_id(
                    source=WebhookSource.CONNECTSAFELY.value,
                    external_id=message_id,
                )
                if existing_reply:
                    logger.info(
                        "duplicate_linkedin_dm_skipped",
                        webhook_id=webhook_id,
                        external_id=message_id,
                    )
                else:
                    # Create reply record for LinkedIn DM (with race condition protection)
                    try:
                        email_reply = await reply_repo.create_from_webhook(
                            contact_id=contact.id,
                            source=WebhookSource.CONNECTSAFELY.value,
                            external_id=message_id,
                            body_text=message_text,
                            subject="LinkedIn DM",
                            received_at=received_at,
                        )
                        await session.flush()
                        reply_id = str(email_reply.id)

                        # Update contact last response
                        contact.last_response_at = received_at
                        await session.flush()

                        logger.info(
                            "linkedin_dm_reply_created",
                            webhook_id=webhook_id,
                            reply_id=reply_id,
                            contact_id=str(contact.id),
                        )
                    except IntegrityError:
                        # Race condition: another process created this reply
                        await session.rollback()
                        logger.info(
                            "duplicate_linkedin_dm_race_condition",
                            webhook_id=webhook_id,
                            external_id=message_id,
                        )

            await session.commit()

            # Queue categorization after commit (if we created a reply)
            if reply_id:
                categorize_email_reply.delay(
                    reply_id=reply_id,
                    subject="LinkedIn DM",
                    body=message_text,
                    context=None,
                )
                logger.info(
                    "linkedin_dm_categorization_queued",
                    webhook_id=webhook_id,
                    reply_id=reply_id,
                )

            return {
                "status": "processed",
                "webhook_id": webhook_id,
                "event_type": event_type,
                "contact_id": str(contact.id) if contact else None,
                "reply_id": reply_id,
                "processed_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            await session.rollback()
            raise e


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def process_connectsafely_webhook(
    self,
    webhook_id: str,
    payload: dict,
    source: str,
    received_at: str,
) -> dict:
    """
    Process ConnectSafely (LinkedIn) webhook asynchronously.

    Handles:
    - Connection request accepted/rejected
    - LinkedIn DM replies
    - Profile engagement
    """
    try:
        logger.info(
            "processing_connectsafely_webhook",
            webhook_id=webhook_id,
            event_type=payload.get("event_type"),
        )

        result = run_async(
            _process_connectsafely_webhook_async(
                webhook_id=webhook_id,
                payload=payload,
                source=source,
                received_at_str=received_at,
            )
        )

        return result

    except Exception as e:
        logger.error(
            "connectsafely_webhook_processing_failed",
            webhook_id=webhook_id,
            error=str(e),
        )
        raise self.retry(exc=e)


async def _process_heyreach_webhook_async(
    webhook_id: str,
    payload: dict,
    source: str,
    received_at_str: str,
) -> dict:
    """Async implementation of HeyReach webhook processing."""
    from app.db.models.webhook_log import WebhookLog
    from app.db.repositories.contact import ContactRepository
    from app.db.repositories.email_reply import EmailReplyRepository
    from app.workers.categorization_tasks import categorize_email_reply

    received_at = datetime.fromisoformat(received_at_str)

    async with async_session_factory() as session:
        try:
            event_type = payload.get("event_type")
            linkedin_url = payload.get("linkedin_url")
            email = payload.get("email")
            message_text = payload.get("message_text")
            message_id = payload.get("message_id") or str(uuid4())
            first_name = payload.get("first_name")
            last_name = payload.get("last_name")
            company_name = payload.get("company_name")
            campaign_id = payload.get("campaign_id")

            contact_repo = ContactRepository(session)
            reply_repo = EmailReplyRepository(session)

            # Try to find contact by email or LinkedIn URL
            contact = None
            created = False
            if email:
                contact = await contact_repo.get_by_email(email)

            if not contact and linkedin_url:
                contact = await contact_repo.get_by_linkedin_url(linkedin_url)

            # Create contact if not found but we have enough info
            if not contact and (email or linkedin_url):
                contact, created = await contact_repo.get_or_create_by_email(
                    email=email or f"linkedin_{message_id}@heyreach.placeholder",
                    first_name=first_name,
                    last_name=last_name,
                    company_name=company_name,
                    linkedin_url=linkedin_url,
                )

            # Log webhook
            webhook_log = WebhookLog(
                source=WebhookSource.HEYREACH.value,
                endpoint="/webhook/heyreach",
                method="POST",
                headers={},
                payload=payload,
                processed=True,
                response_status=200,
                received_at=received_at,
            )
            session.add(webhook_log)

            reply_id = None

            # Handle different event types
            if event_type == "connection_accepted" and contact and linkedin_url:
                contact.linkedin_url = linkedin_url
                logger.info(
                    "heyreach_connection_updated",
                    webhook_id=webhook_id,
                    contact_id=str(contact.id),
                )

            elif event_type == "connection_rejected" and contact:
                logger.info(
                    "heyreach_connection_rejected",
                    webhook_id=webhook_id,
                    contact_id=str(contact.id) if contact else None,
                )

            # Handle LinkedIn message replies - categorize them
            elif event_type == "message_received" and message_text and contact:
                # Check for duplicate
                existing_reply = await reply_repo.get_by_external_id(
                    source=WebhookSource.HEYREACH.value,
                    external_id=message_id,
                )
                if existing_reply:
                    logger.info(
                        "duplicate_heyreach_message_skipped",
                        webhook_id=webhook_id,
                        external_id=message_id,
                    )
                else:
                    # Create reply record (with race condition protection)
                    try:
                        email_reply = await reply_repo.create_from_webhook(
                            contact_id=contact.id,
                            source=WebhookSource.HEYREACH.value,
                            external_id=message_id,
                            body_text=message_text,
                            subject="LinkedIn DM (HeyReach)",
                            received_at=received_at,
                            campaign_external_id=campaign_id,
                        )
                        await session.flush()
                        reply_id = str(email_reply.id)

                        # Update contact last response
                        contact.last_response_at = received_at
                        await session.flush()

                        logger.info(
                            "heyreach_message_reply_created",
                            webhook_id=webhook_id,
                            reply_id=reply_id,
                            contact_id=str(contact.id),
                        )
                    except IntegrityError:
                        await session.rollback()
                        logger.info(
                            "duplicate_heyreach_message_race_condition",
                            webhook_id=webhook_id,
                            external_id=message_id,
                        )

            await session.commit()

            # Queue categorization after commit (if we created a reply)
            if reply_id:
                categorize_email_reply.delay(
                    reply_id=reply_id,
                    subject="LinkedIn DM (HeyReach)",
                    body=message_text,
                    context=None,
                )
                logger.info(
                    "heyreach_message_categorization_queued",
                    webhook_id=webhook_id,
                    reply_id=reply_id,
                )

            return {
                "status": "processed",
                "webhook_id": webhook_id,
                "event_type": event_type,
                "contact_id": str(contact.id) if contact else None,
                "contact_created": created,
                "reply_id": reply_id,
                "processed_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            await session.rollback()
            raise e


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def process_heyreach_webhook(
    self,
    webhook_id: str,
    payload: dict,
    source: str,
    received_at: str,
) -> dict:
    """
    Process HeyReach (LinkedIn automation) webhook asynchronously.

    Handles:
    - Connection request accepted/rejected
    - LinkedIn DM replies
    - Campaign events
    """
    try:
        logger.info(
            "processing_heyreach_webhook",
            webhook_id=webhook_id,
            event_type=payload.get("event_type"),
        )

        result = run_async(
            _process_heyreach_webhook_async(
                webhook_id=webhook_id,
                payload=payload,
                source=source,
                received_at_str=received_at,
            )
        )

        return result

    except Exception as e:
        logger.error(
            "heyreach_webhook_processing_failed",
            webhook_id=webhook_id,
            error=str(e),
        )
        raise self.retry(exc=e)

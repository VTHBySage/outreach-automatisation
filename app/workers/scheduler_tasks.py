"""Scheduled background tasks for re-engagement and maintenance."""

from datetime import datetime
from uuid import UUID

from celery import shared_task

from app.core.constants import LeadSource, WebhookSource
from app.core.logging import get_logger
from app.core.utils import run_async
from app.db.session import async_session_factory

logger = get_logger(__name__)


async def _process_reengagement_contacts_async(
    batch_size: int = 100,
    reengagement_campaign_id: str | None = None,
) -> dict:
    """Async implementation of re-engagement contact processing."""
    from app.core.redis_lock import get_redis_lock
    from app.db.models.contact import Contact
    from app.integrations.hubspot import HubSpotContacts
    from app.integrations.smartlead import SmartLeadClient
    from app.services.linkedin import LinkedInApprovalService
    from app.services.scheduler import SchedulerService

    # Acquire distributed lock to prevent duplicate processing
    # Lock timeout of 30 minutes - should be plenty for batch processing
    redis_lock = get_redis_lock()
    async with redis_lock.lock("reengagement_processing", timeout=1800) as acquired:
        if not acquired:
            logger.warning(
                "reengagement_lock_not_acquired",
                reason="another_instance_running",
            )
            return {
                "status": "skipped",
                "reason": "lock_not_acquired",
                "processed": 0,
            }

        async with async_session_factory() as session:
            try:
                scheduler_service = SchedulerService(session)
                linkedin_service = LinkedInApprovalService(session)

                # Get contacts due for re-engagement
                contacts = await scheduler_service.get_contacts_due_for_reengagement(
                    limit=batch_size
                )

                if not contacts:
                    logger.info("no_contacts_due_for_reengagement")
                    return {
                        "status": "complete",
                        "processed": 0,
                        "added_to_smartlead": 0,
                        "queued_for_linkedin": 0,
                    }

                logger.info(
                    "processing_reengagement_contacts",
                    count=len(contacts),
                )

                smartlead_client = SmartLeadClient()
                hubspot_contacts = HubSpotContacts()

                added_to_smartlead = 0
                queued_for_linkedin = 0
                errors = []

                for contact in contacts:
                    try:
                        # Determine which platform to use based on source or preference
                        # Default to SmartLead for email re-engagement
                        use_linkedin = (
                            contact.source == LeadSource.LINKEDIN_NAVIGATOR.value
                            or contact.linkedin_url
                        )

                        if use_linkedin and contact.linkedin_url:
                            # Queue LinkedIn message for human approval (REQUIRED)
                            # All LinkedIn messages must be approved before sending
                            message = f"Hi {contact.first_name or 'there'}, following up on our previous conversation. Would love to reconnect!"
                            context = f"Re-engagement outreach. Original category: {contact.current_category or 'N/A'}"

                            await linkedin_service.queue_connection_request(
                                contact=contact,
                                profile_url=contact.linkedin_url,
                                message=message,
                                context=context,
                            )
                            queued_for_linkedin += 1
                            logger.info(
                                "linkedin_reengagement_queued",
                                contact_id=str(contact.id),
                                email=contact.email,
                            )
                        else:
                            # Add to SmartLead for email re-engagement
                            campaign_id = reengagement_campaign_id
                            if not campaign_id:
                                # Use a default re-engagement campaign if not specified
                                campaigns = await smartlead_client.get_campaigns(status="active")
                                reengagement_campaigns = [
                                    c for c in campaigns
                                    if "reengagement" in c.get("name", "").lower()
                                    or "re-engagement" in c.get("name", "").lower()
                                ]
                                if reengagement_campaigns:
                                    campaign_id = reengagement_campaigns[0].get("id")

                            if campaign_id:
                                # Add custom field indicating this is a re-engagement
                                custom_fields = {
                                    "re_engagement_category": contact.re_engagement_category or "",
                                    "original_category": contact.current_category or "",
                                }

                                await smartlead_client.add_lead_to_campaign(
                                    campaign_id=campaign_id,
                                    email=contact.email,
                                    first_name=contact.first_name,
                                    last_name=contact.last_name,
                                    company_name=contact.company_name,
                                    custom_fields=custom_fields,
                                )
                                added_to_smartlead += 1
                                logger.info(
                                    "contact_added_to_smartlead",
                                    contact_id=str(contact.id),
                                    email=contact.email,
                                    campaign_id=campaign_id,
                                )
                            else:
                                logger.warning(
                                    "no_reengagement_campaign_found",
                                    contact_id=str(contact.id),
                                )

                        # Update HubSpot with re-engagement status
                        if contact.hubspot_contact_id:
                            await hubspot_contacts.update_contact(
                                contact_id=contact.hubspot_contact_id,
                                properties={
                                    "re_engagement_status": "in_progress",
                                    "re_engagement_date": datetime.utcnow().isoformat(),
                                },
                            )

                        # Clear re-engagement date (will be reset if they respond)
                        await scheduler_service.clear_reengagement(contact)

                    except Exception as e:
                        logger.error(
                            "reengagement_processing_error",
                            contact_id=str(contact.id),
                            error=str(e),
                        )
                        errors.append({
                            "contact_id": str(contact.id),
                            "error": str(e),
                        })

                await session.commit()

                return {
                    "status": "complete",
                    "processed": len(contacts),
                    "added_to_smartlead": added_to_smartlead,
                    "queued_for_linkedin": queued_for_linkedin,
                    "errors": errors,
                }

            except Exception as e:
                await session.rollback()
                raise e


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
)
def process_reengagement_contacts(
    self,
    batch_size: int = 100,
    reengagement_campaign_id: str | None = None,
) -> dict:
    """
    Process contacts due for re-engagement.

    This task should be scheduled to run periodically (e.g., daily or weekly).

    Flow:
    1. Query contacts where re_engagement_date <= now
    2. For each contact, add to SmartLead or ConnectSafely sequence
    3. Update HubSpot fields
    4. Clear re-engagement date

    Args:
        batch_size: Number of contacts to process per run
        reengagement_campaign_id: Specific SmartLead campaign ID for re-engagement
    """
    try:
        logger.info(
            "starting_reengagement_processing",
            batch_size=batch_size,
        )

        result = run_async(
            _process_reengagement_contacts_async(
                batch_size=batch_size,
                reengagement_campaign_id=reengagement_campaign_id,
            )
        )

        logger.info(
            "reengagement_processing_complete",
            processed=result.get("processed", 0),
            added_to_smartlead=result.get("added_to_smartlead", 0),
            queued_for_linkedin=result.get("queued_for_linkedin", 0),
        )

        return result

    except Exception as e:
        logger.error(
            "reengagement_processing_failed",
            error=str(e),
        )
        raise self.retry(exc=e)


async def _cleanup_stale_webhook_logs_async(days_old: int = 30) -> dict:
    """Async implementation of webhook log cleanup."""
    from datetime import timedelta

    from sqlalchemy import delete

    from app.db.models.webhook_log import WebhookLog

    async with async_session_factory() as session:
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            stmt = delete(WebhookLog).where(WebhookLog.received_at < cutoff_date)
            result = await session.execute(stmt)
            await session.commit()

            deleted_count = result.rowcount

            logger.info(
                "webhook_logs_cleaned",
                deleted_count=deleted_count,
                days_old=days_old,
            )

            return {
                "status": "complete",
                "deleted_count": deleted_count,
            }

        except Exception as e:
            await session.rollback()
            raise e


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def cleanup_stale_webhook_logs(
    self,
    days_old: int = 30,
) -> dict:
    """
    Clean up old webhook logs to prevent database bloat.

    Should be scheduled to run weekly.

    Args:
        days_old: Delete logs older than this many days
    """
    try:
        logger.info(
            "starting_webhook_log_cleanup",
            days_old=days_old,
        )

        result = run_async(_cleanup_stale_webhook_logs_async(days_old=days_old))
        return result

    except Exception as e:
        logger.error(
            "webhook_log_cleanup_failed",
            error=str(e),
        )
        raise self.retry(exc=e)


async def _sync_all_pending_tasks_async() -> dict:
    """Async implementation to sync all pending tasks to HubSpot."""
    from app.services.tasks import TaskService
    from app.workers.hubspot_tasks import create_hubspot_task

    async with async_session_factory() as session:
        task_service = TaskService(session)
        pending_tasks = await task_service.get_pending_tasks(limit=200)

        queued_count = 0
        for task in pending_tasks:
            create_hubspot_task.delay(task_id=str(task.id))
            queued_count += 1

        return {
            "status": "complete",
            "tasks_queued": queued_count,
        }


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=120,
)
def sync_all_pending_tasks(self) -> dict:
    """
    Sync all pending tasks to HubSpot.

    Catchup task to ensure all tasks are synced.
    Should be scheduled hourly.
    """
    try:
        logger.info("starting_pending_tasks_sync")

        result = run_async(_sync_all_pending_tasks_async())

        logger.info(
            "pending_tasks_sync_complete",
            tasks_queued=result.get("tasks_queued", 0),
        )

        return result

    except Exception as e:
        logger.error(
            "pending_tasks_sync_failed",
            error=str(e),
        )
        raise self.retry(exc=e)


# Celery beat schedule configuration
# Add to celery_app.py or settings:
#
# CELERYBEAT_SCHEDULE = {
#     'process-reengagement-daily': {
#         'task': 'app.workers.scheduler_tasks.process_reengagement_contacts',
#         'schedule': crontab(hour=9, minute=0),  # 9 AM daily
#         'args': (100,),
#     },
#     'cleanup-webhook-logs-weekly': {
#         'task': 'app.workers.scheduler_tasks.cleanup_stale_webhook_logs',
#         'schedule': crontab(hour=3, minute=0, day_of_week='sunday'),  # 3 AM Sundays
#         'args': (30,),
#     },
#     'sync-pending-tasks-hourly': {
#         'task': 'app.workers.scheduler_tasks.sync_all_pending_tasks',
#         'schedule': crontab(minute=0),  # Every hour
#     },
# }

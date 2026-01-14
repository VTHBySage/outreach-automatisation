"""HubSpot synchronization tasks."""

from datetime import datetime
from uuid import UUID

from celery import shared_task

from app.core.constants import TaskPriority, TaskStatus
from app.core.logging import get_logger
from app.core.utils import run_async
from app.db.session import async_session_factory

logger = get_logger(__name__)


async def _sync_contact_to_hubspot_async(contact_id: str) -> dict:
    """Async implementation of contact sync to HubSpot."""
    from app.db.models.contact import Contact
    from app.integrations.hubspot import HubSpotContacts

    async with async_session_factory() as session:
        try:
            contact_uuid = UUID(contact_id)
            contact = await session.get(Contact, contact_uuid)

            if not contact:
                logger.error("contact_not_found", contact_id=contact_id)
                return {"status": "error", "reason": "contact_not_found"}

            # Skip if already synced
            if contact.hubspot_contact_id:
                logger.info(
                    "contact_already_synced",
                    contact_id=contact_id,
                    hubspot_id=contact.hubspot_contact_id,
                )
                return {
                    "status": "already_synced",
                    "contact_id": contact_id,
                    "hubspot_contact_id": contact.hubspot_contact_id,
                }

            # Sync to HubSpot
            hubspot_contacts = HubSpotContacts()
            hs_contact = await hubspot_contacts.get_or_create_contact(
                email=contact.email,
                first_name=contact.first_name,
                last_name=contact.last_name,
                company=contact.company_name,
                phone=contact.phone,
            )

            # Update local record with HubSpot ID
            hubspot_contact_id = hs_contact.get("id")
            if hubspot_contact_id:
                contact.hubspot_contact_id = hubspot_contact_id
                await session.commit()

            logger.info(
                "contact_synced_to_hubspot",
                contact_id=contact_id,
                hubspot_contact_id=hubspot_contact_id,
            )

            return {
                "status": "synced",
                "contact_id": contact_id,
                "hubspot_contact_id": hubspot_contact_id,
            }

        except Exception as e:
            await session.rollback()
            raise e


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    rate_limit="10/m",  # HubSpot rate limiting
)
def sync_contact_to_hubspot(self, contact_id: str) -> dict:
    """
    Sync contact to HubSpot CRM.

    Creates or updates HubSpot contact record.
    """
    # Validate UUID format before processing
    try:
        UUID(contact_id)
    except ValueError:
        logger.error(
            "invalid_contact_id_format",
            contact_id=contact_id,
        )
        return {"status": "error", "reason": "invalid_contact_id_format"}

    try:
        logger.info(
            "syncing_contact_to_hubspot",
            contact_id=contact_id,
        )

        result = run_async(_sync_contact_to_hubspot_async(contact_id))
        return result

    except Exception as e:
        logger.error(
            "hubspot_contact_sync_failed",
            contact_id=contact_id,
            error=str(e),
        )
        raise self.retry(exc=e)


async def _create_hubspot_task_async(task_id: str) -> dict:
    """Async implementation of HubSpot task creation."""
    from app.db.models.contact import Contact
    from app.db.models.task import Task
    from app.integrations.hubspot import HubSpotContacts, HubSpotTasks

    async with async_session_factory() as session:
        try:
            task_uuid = UUID(task_id)
            task = await session.get(Task, task_uuid)

            if not task:
                logger.error("task_not_found", task_id=task_id)
                return {"status": "error", "reason": "task_not_found"}

            # Skip if already synced
            if task.hubspot_task_id:
                logger.info(
                    "task_already_synced",
                    task_id=task_id,
                    hubspot_task_id=task.hubspot_task_id,
                )
                return {
                    "status": "already_synced",
                    "task_id": task_id,
                    "hubspot_task_id": task.hubspot_task_id,
                }

            # Get contact
            contact = await session.get(Contact, task.contact_id)
            if not contact:
                logger.error("contact_not_found", contact_id=str(task.contact_id))
                return {"status": "error", "reason": "contact_not_found"}

            # Ensure contact is synced to HubSpot first
            if not contact.hubspot_contact_id:
                hubspot_contacts = HubSpotContacts()
                hs_contact = await hubspot_contacts.get_or_create_contact(
                    email=contact.email,
                    first_name=contact.first_name,
                    last_name=contact.last_name,
                    company=contact.company_name,
                    phone=contact.phone,
                )
                contact.hubspot_contact_id = hs_contact.get("id")
                await session.flush()

            # Create task in HubSpot
            hubspot_tasks = HubSpotTasks()
            priority = TaskPriority(task.priority)

            hs_task = await hubspot_tasks.create_task(
                title=task.title,
                due_date=task.due_date,
                priority=priority,
                contact_id=contact.hubspot_contact_id,
                description=task.description,
            )

            # Update local task with HubSpot ID
            hubspot_task_id = hs_task.get("id")
            if hubspot_task_id:
                task.hubspot_task_id = hubspot_task_id
                task.sync_status = TaskStatus.SYNCED.value
                task.synced_at = datetime.utcnow()

            await session.commit()

            logger.info(
                "task_synced_to_hubspot",
                task_id=task_id,
                hubspot_task_id=hubspot_task_id,
            )

            return {
                "status": "synced",
                "task_id": task_id,
                "hubspot_task_id": hubspot_task_id,
                "hubspot_task_url": hubspot_tasks.get_task_url(hubspot_task_id) if hubspot_task_id else None,
            }

        except Exception as e:
            # Update sync status to failed
            try:
                await session.rollback()
                task = await session.get(Task, UUID(task_id))
                if task:
                    task.sync_status = TaskStatus.FAILED.value
                    task.sync_error = str(e)
                    await session.commit()
            except Exception as update_error:
                logger.error(
                    "failed_to_update_task_status",
                    task_id=task_id,
                    original_error=str(e),
                    update_error=str(update_error),
                )
            raise e


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    rate_limit="10/m",  # HubSpot rate limiting
)
def create_hubspot_task(self, task_id: str) -> dict:
    """
    Create task in HubSpot.

    Flow:
    1. Load task from database
    2. Ensure contact is synced
    3. Create HubSpot task
    4. Associate with contact
    5. Update local task with HubSpot ID
    """
    # Validate UUID format before processing
    try:
        UUID(task_id)
    except ValueError:
        logger.error(
            "invalid_task_id_format",
            task_id=task_id,
        )
        return {"status": "error", "reason": "invalid_task_id_format"}

    try:
        logger.info(
            "creating_hubspot_task",
            task_id=task_id,
        )

        result = run_async(_create_hubspot_task_async(task_id))
        return result

    except Exception as e:
        logger.error(
            "hubspot_task_creation_failed",
            task_id=task_id,
            error=str(e),
        )
        raise self.retry(exc=e)


async def _sync_pending_tasks_async() -> dict:
    """Async implementation of pending tasks sync."""
    from app.services.tasks import TaskService

    async with async_session_factory() as session:
        task_service = TaskService(session)
        pending_tasks = await task_service.get_pending_tasks(limit=50)

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
    max_retries=3,
    default_retry_delay=60,
)
def sync_pending_tasks_to_hubspot(self) -> dict:
    """
    Batch sync all pending tasks to HubSpot.

    Run periodically to catch any tasks that weren't synced.
    """
    try:
        logger.info("syncing_pending_tasks")

        result = run_async(_sync_pending_tasks_async())

        logger.info(
            "pending_tasks_queued",
            tasks_queued=result["tasks_queued"],
        )

        return result

    except Exception as e:
        logger.error(
            "pending_tasks_sync_failed",
            error=str(e),
        )
        raise self.retry(exc=e)

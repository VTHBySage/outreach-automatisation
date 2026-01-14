"""LinkedIn message processing tasks."""

from celery import shared_task

from app.core.constants import LinkedInMessageStatus, LinkedInMessageType
from app.core.logging import get_logger
from app.core.utils import run_async
from app.db.session import async_session_factory

logger = get_logger(__name__)


async def _process_approved_linkedin_messages_async(batch_size: int = 20) -> dict:
    """
    Process LinkedIn messages that have been approved.

    This task sends messages that were approved via HubSpot task completion.
    """
    from sqlalchemy import select

    from app.db.models.linkedin_message import PendingLinkedInMessage
    from app.integrations.connectsafely import ConnectSafelyClient
    from app.services.linkedin import LinkedInApprovalService

    async with async_session_factory() as session:
        try:
            service = LinkedInApprovalService(session)
            client = ConnectSafelyClient()

            # Get approved messages
            approved_messages = await service.get_approved_messages(limit=batch_size)

            if not approved_messages:
                logger.info("no_approved_linkedin_messages")
                return {
                    "status": "complete",
                    "processed": 0,
                    "sent": 0,
                    "failed": 0,
                }

            logger.info(
                "processing_approved_linkedin_messages",
                count=len(approved_messages),
            )

            sent_count = 0
            failed_count = 0
            errors = []

            for message in approved_messages:
                try:
                    # Send based on message type
                    if message.message_type == LinkedInMessageType.CONNECTION_REQUEST.value:
                        await client.send_connection_request(
                            profile_url=message.profile_url,
                            message=message.message_content,
                        )
                    elif message.message_type == LinkedInMessageType.DIRECT_MESSAGE.value:
                        await client.send_direct_message(
                            profile_url=message.profile_url,
                            message=message.message_content or "",
                        )

                    # Mark as sent
                    await service.mark_as_sent(message.id)
                    sent_count += 1

                    logger.info(
                        "linkedin_message_sent",
                        message_id=str(message.id),
                        message_type=message.message_type,
                        profile_url=message.profile_url,
                    )

                except Exception as e:
                    # Mark as failed
                    await service.mark_as_failed(message.id, str(e))
                    failed_count += 1
                    errors.append({
                        "message_id": str(message.id),
                        "error": str(e),
                    })

            await session.commit()

            return {
                "status": "complete",
                "processed": len(approved_messages),
                "sent": sent_count,
                "failed": failed_count,
                "errors": errors if errors else None,
            }

        except Exception as e:
            await session.rollback()
            raise e


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    rate_limit="20/m",  # LinkedIn rate limiting
)
def process_approved_linkedin_messages(
    self,
    batch_size: int = 20,
) -> dict:
    """
    Process LinkedIn messages that have been approved.

    This task should be scheduled to run frequently (every 5-10 minutes)
    to ensure timely delivery of approved messages.

    Human approval workflow:
    1. Sales rep completes HubSpot approval task
    2. Webhook updates message status to APPROVED
    3. This task sends the approved message
    4. Message status updated to SENT or FAILED
    """
    try:
        logger.info(
            "starting_linkedin_message_processing",
            batch_size=batch_size,
        )

        result = run_async(
            _process_approved_linkedin_messages_async(batch_size=batch_size)
        )

        logger.info(
            "linkedin_message_processing_complete",
            processed=result.get("processed", 0),
            sent=result.get("sent", 0),
            failed=result.get("failed", 0),
        )

        return result

    except Exception as e:
        logger.error(
            "linkedin_message_processing_failed",
            error=str(e),
        )
        raise self.retry(exc=e)


async def _check_task_completion_for_approval_async() -> dict:
    """
    Check HubSpot tasks for LinkedIn approval.

    When a task is marked complete in HubSpot, approve the linked LinkedIn message.
    When a task is deleted, reject the linked message.
    """
    from sqlalchemy import select

    from app.core.constants import TaskStatus
    from app.db.models.linkedin_message import PendingLinkedInMessage
    from app.db.models.task import Task
    from app.services.linkedin import LinkedInApprovalService

    async with async_session_factory() as session:
        try:
            service = LinkedInApprovalService(session)

            # Find pending LinkedIn messages with completed approval tasks
            stmt = (
                select(PendingLinkedInMessage)
                .join(Task, PendingLinkedInMessage.approval_task_id == Task.id)
                .where(
                    PendingLinkedInMessage.status == LinkedInMessageStatus.PENDING_APPROVAL.value,
                    Task.sync_status == TaskStatus.COMPLETED.value,
                )
            )
            result = await session.execute(stmt)
            messages_to_approve = list(result.scalars().all())

            approved_count = 0
            for message in messages_to_approve:
                await service.approve_message(
                    message_id=message.id,
                    approved_by="hubspot_task_completion",
                )
                approved_count += 1

            await session.commit()

            logger.info(
                "linkedin_approvals_processed",
                approved_count=approved_count,
            )

            return {
                "status": "complete",
                "approved_count": approved_count,
            }

        except Exception as e:
            await session.rollback()
            raise e


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def check_task_completion_for_approval(self) -> dict:
    """
    Check for completed HubSpot tasks to approve LinkedIn messages.

    This task bridges HubSpot task completion with LinkedIn message approval.
    Should be scheduled to run every 5 minutes.
    """
    try:
        logger.info("checking_linkedin_approval_tasks")

        result = run_async(_check_task_completion_for_approval_async())
        return result

    except Exception as e:
        logger.error(
            "linkedin_approval_check_failed",
            error=str(e),
        )
        raise self.retry(exc=e)

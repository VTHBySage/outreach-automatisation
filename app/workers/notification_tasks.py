"""MS Teams notification tasks."""

from datetime import datetime
from uuid import UUID

from celery import shared_task

from app.core.constants import TaskPriority
from app.core.logging import get_logger
from app.core.utils import run_async
from app.db.session import async_session_factory

logger = get_logger(__name__)


async def _send_teams_notification_async(
    task_id: str,
    contact_id: str,
) -> dict:
    """Async implementation of Teams notification sending."""
    from app.db.models.contact import Contact
    from app.db.models.email_reply import EmailReply
    from app.db.models.task import Task
    from app.integrations.hubspot import HubSpotTasks
    from app.integrations.openai import OpenAIClient
    from app.services.notifications import NotificationService

    async with async_session_factory() as session:
        try:
            task_uuid = UUID(task_id)
            contact_uuid = UUID(contact_id)

            # Load task and contact
            task = await session.get(Task, task_uuid)
            contact = await session.get(Contact, contact_uuid)

            if not task:
                logger.error("task_not_found", task_id=task_id)
                return {"status": "error", "reason": "task_not_found"}

            if not contact:
                logger.error("contact_not_found", contact_id=contact_id)
                return {"status": "error", "reason": "contact_not_found"}

            # Check if notification already sent
            if task.ms_teams_message_id:
                logger.info(
                    "notification_already_sent",
                    task_id=task_id,
                    message_id=task.ms_teams_message_id,
                )
                return {
                    "status": "already_sent",
                    "task_id": task_id,
                    "message_id": task.ms_teams_message_id,
                }

            # Check priority - only notify for HIGH and HIGHEST
            try:
                priority = TaskPriority(task.priority)
                if priority not in {TaskPriority.HIGHEST, TaskPriority.HIGH}:
                    logger.debug(
                        "notification_skipped_low_priority",
                        task_id=task_id,
                        priority=task.priority,
                    )
                    return {
                        "status": "skipped",
                        "reason": "low_priority",
                        "task_id": task_id,
                        "priority": task.priority,
                    }
            except ValueError:
                logger.warning(
                    "invalid_task_priority",
                    task_id=task_id,
                    priority=task.priority,
                )

            # Get HubSpot task URL if available
            hubspot_task_url = None
            if task.hubspot_task_id:
                hubspot_tasks = HubSpotTasks()
                hubspot_task_url = hubspot_tasks.get_task_url(task.hubspot_task_id)

            # Generate draft message using AI
            draft_message = None
            meeting_agenda = None
            try:
                # Get email context from triggered reply if available
                email_context = ""
                if task.triggered_by_reply_id:
                    reply = await session.get(EmailReply, task.triggered_by_reply_id)
                    if reply:
                        email_context = f"Subject: {reply.subject or 'No subject'}\n\nBody: {reply.body_text[:500]}"

                openai_client = OpenAIClient()

                # Generate draft response message
                draft_message = await openai_client.generate_draft_message(
                    context=email_context or f"Lead interested in B2B insurance services. Task: {task.task_type}",
                    category=task.category or "interested",
                    lead_name=contact.full_name,
                )

                # Generate meeting agenda for appointment-related tasks
                if "appointment" in task.task_type.lower() or "call" in task.task_type.lower() or "meeting" in task.task_type.lower():
                    meeting_agenda = await _generate_meeting_agenda(
                        openai_client=openai_client,
                        contact=contact,
                        task_type=task.task_type,
                        context=email_context,
                    )

                logger.info(
                    "draft_message_generated",
                    task_id=task_id,
                    has_draft=bool(draft_message),
                    has_agenda=bool(meeting_agenda),
                )

            except Exception as e:
                logger.warning(
                    "draft_generation_failed",
                    task_id=task_id,
                    error=str(e),
                )
                # Continue without draft message - not a critical failure

            # Send notification
            notification_service = NotificationService()
            message_id = await notification_service.notify_task_created(
                task=task,
                contact=contact,
                hubspot_task_url=hubspot_task_url,
                draft_message=draft_message,
                meeting_agenda=meeting_agenda,
            )

            # Update task with notification info
            if message_id:
                task.ms_teams_message_id = message_id
                task.notification_sent_at = datetime.utcnow()
                await session.commit()

                logger.info(
                    "notification_sent_successfully",
                    task_id=task_id,
                    message_id=message_id,
                )

                return {
                    "status": "sent",
                    "task_id": task_id,
                    "message_id": message_id,
                }

            return {
                "status": "skipped",
                "reason": "notification_returned_none",
                "task_id": task_id,
            }

        except Exception as e:
            await session.rollback()
            raise e


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def send_teams_notification(
    self,
    task_id: str,
    contact_id: str,
) -> dict:
    """
    Send MS Teams notification for a high-priority task.

    Only sends for HIGH and HIGHEST priority tasks.

    Flow:
    1. Load Task and Contact from database
    2. Check if notification already sent
    3. Check task priority
    4. Get HubSpot task URL if available
    5. Send notification via MS Teams webhook
    6. Update Task with message ID
    """
    try:
        logger.info(
            "sending_teams_notification",
            task_id=task_id,
            contact_id=contact_id,
        )

        result = run_async(
            _send_teams_notification_async(
                task_id=task_id,
                contact_id=contact_id,
            )
        )

        return result

    except Exception as e:
        logger.error(
            "teams_notification_failed",
            task_id=task_id,
            error=str(e),
        )
        raise self.retry(exc=e)


async def _generate_meeting_agenda(
    openai_client,
    contact,
    task_type: str,
    context: str,
) -> str:
    """Generate a meeting agenda using AI."""
    try:
        system_prompt = """You are a B2B sales professional preparing for a discovery call.
        Generate a brief, professional meeting agenda (3-5 bullet points).
        Focus on understanding the prospect's needs and presenting value.
        Keep it concise and actionable."""

        user_prompt = f"""Generate a meeting agenda for a call with:
Lead Name: {contact.full_name}
Company: {contact.company_name}
Task Type: {task_type}
Context: {context or 'Initial discovery call for B2B insurance services'}

Create a brief agenda (3-5 bullet points)."""

        response = await openai_client.client.chat.completions.create(
            model=openai_client.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=200,
            temperature=0.7,
        )

        # Validate response has choices
        if not response.choices:
            logger.warning("meeting_agenda_no_choices")
            return ""

        return response.choices[0].message.content or ""

    except Exception as e:
        logger.warning(
            "meeting_agenda_generation_failed",
            error=str(e),
        )
        return ""


async def _send_batch_summary_async(task_ids: list[str]) -> dict:
    """Async implementation of batch summary notification."""
    from app.db.models.contact import Contact
    from app.db.models.task import Task
    from app.integrations.msteams import MSTeamsClient

    async with async_session_factory() as session:
        try:
            # Load all tasks
            tasks_data = []
            for task_id in task_ids:
                task_uuid = UUID(task_id)
                task = await session.get(Task, task_uuid)
                if task:
                    contact = await session.get(Contact, task.contact_id)
                    if contact:
                        tasks_data.append({
                            "task": task,
                            "contact": contact,
                            "priority": TaskPriority(task.priority) if task.priority else TaskPriority.MEDIUM,
                        })

            if not tasks_data:
                logger.warning("no_tasks_found_for_batch", task_ids=task_ids)
                return {"status": "skipped", "reason": "no_tasks_found"}

            # Group by priority
            highest_tasks = [t for t in tasks_data if t["priority"] == TaskPriority.HIGHEST]
            high_tasks = [t for t in tasks_data if t["priority"] == TaskPriority.HIGH]
            other_tasks = [t for t in tasks_data if t["priority"] not in {TaskPriority.HIGHEST, TaskPriority.HIGH}]

            # Build summary card
            card = _build_batch_summary_card(
                highest_tasks=highest_tasks,
                high_tasks=high_tasks,
                other_tasks=other_tasks,
                total_count=len(tasks_data),
            )

            # Send notification
            client = MSTeamsClient()
            message_id = await client.send_message(card)

            logger.info(
                "batch_notification_sent",
                message_id=message_id,
                task_count=len(tasks_data),
            )

            return {
                "status": "sent",
                "message_id": message_id,
                "task_count": len(tasks_data),
                "highest_count": len(highest_tasks),
                "high_count": len(high_tasks),
            }

        except Exception as e:
            await session.rollback()
            raise e


def _build_batch_summary_card(
    highest_tasks: list,
    high_tasks: list,
    other_tasks: list,
    total_count: int,
) -> dict:
    """Build adaptive card for batch summary."""
    body = [
        {
            "type": "TextBlock",
            "text": f"📋 Task Summary: {total_count} New Tasks",
            "weight": "bolder",
            "size": "large",
        },
    ]

    # Highest priority section
    if highest_tasks:
        body.append({
            "type": "TextBlock",
            "text": f"🔴 HIGHEST Priority ({len(highest_tasks)})",
            "weight": "bolder",
            "color": "attention",
        })
        for item in highest_tasks[:5]:  # Limit to 5
            task = item["task"]
            contact = item["contact"]
            body.append({
                "type": "TextBlock",
                "text": f"• {task.title} - {contact.full_name} ({contact.company_name})",
                "wrap": True,
            })

    # High priority section
    if high_tasks:
        body.append({
            "type": "TextBlock",
            "text": f"🟡 HIGH Priority ({len(high_tasks)})",
            "weight": "bolder",
            "color": "warning",
        })
        for item in high_tasks[:5]:  # Limit to 5
            task = item["task"]
            contact = item["contact"]
            body.append({
                "type": "TextBlock",
                "text": f"• {task.title} - {contact.full_name} ({contact.company_name})",
                "wrap": True,
            })

    # Other tasks count
    if other_tasks:
        body.append({
            "type": "TextBlock",
            "text": f"📝 {len(other_tasks)} other tasks also created",
            "isSubtle": True,
        })

    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": body,
                },
            }
        ],
    }


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def send_batch_summary_notification(
    self,
    task_ids: list[str],
) -> dict:
    """
    Send a summary notification for multiple tasks.

    Used for batch processing to avoid notification spam.

    Flow:
    1. Load all tasks and their contacts
    2. Group tasks by priority
    3. Build summary adaptive card
    4. Send to Teams channel
    """
    try:
        logger.info(
            "sending_batch_notification",
            task_count=len(task_ids),
        )

        result = run_async(_send_batch_summary_async(task_ids))
        return result

    except Exception as e:
        logger.error(
            "batch_notification_failed",
            task_count=len(task_ids),
            error=str(e),
        )
        raise self.retry(exc=e)

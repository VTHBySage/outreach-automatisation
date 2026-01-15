"""MS Teams notification service."""

from app.core.constants import SubCategory, TaskPriority, get_notification_message
from app.core.exceptions import NotificationError
from app.core.logging import get_logger
from app.db.models.contact import Contact
from app.db.models.task import Task
from app.integrations.msteams.client import MSTeamsClient
from app.services.notifications.formatter import NotificationContent, NotificationFormatter

logger = get_logger(__name__)


class NotificationService:
    """Service for sending MS Teams notifications."""

    # Only send notifications for high-priority tasks
    NOTIFY_PRIORITIES = {TaskPriority.HIGHEST, TaskPriority.HIGH}

    def __init__(self, msteams_client: MSTeamsClient | None = None):
        self.msteams_client = msteams_client or MSTeamsClient()
        self.formatter = NotificationFormatter()

    async def notify_task_created(
        self,
        task: Task,
        contact: Contact,
        hubspot_task_url: str | None = None,
        draft_message: str | None = None,
        meeting_agenda: str | None = None,
    ) -> str | None:
        """
        Send MS Teams notification for a created task.

        Only sends notifications for HIGH and HIGHEST priority tasks.

        Args:
            task: The created task
            contact: The associated contact
            hubspot_task_url: URL to the HubSpot task
            draft_message: AI-generated draft response
            meeting_agenda: AI-generated meeting agenda

        Returns:
            MS Teams message ID if sent, None if skipped
        """
        try:
            priority = TaskPriority(task.priority)

            # Skip low-priority notifications
            if priority not in self.NOTIFY_PRIORITIES:
                logger.debug(
                    "notification_skipped_low_priority",
                    task_id=str(task.id),
                    priority=priority.value,
                )
                return None

            # Get category-specific notification message (Requirements.md 3.3.2)
            # Use subcategory for more specific messages, fallback to category
            category_message = None
            subcategory_value = task.subcategory or task.category
            if subcategory_value:
                try:
                    subcategory = SubCategory(subcategory_value)
                    category_message = get_notification_message(subcategory)
                except ValueError:
                    pass  # Invalid category, skip custom message

            # Build notification content
            content = NotificationContent(
                title=f"[ACTION REQUIRED] {task.title}",
                priority=priority,
                lead_name=contact.full_name,
                company_name=contact.company_name,
                email=contact.email,
                phone=contact.phone,
                task_description=task.task_type.replace("_", " ").title(),
                hubspot_task_url=hubspot_task_url,
                draft_message=draft_message,
                meeting_agenda=meeting_agenda,
                category_message=category_message,
            )

            # Format and send
            card = self.formatter.format_adaptive_card(content)
            message_id = await self.msteams_client.send_message(card)

            logger.info(
                "notification_sent",
                task_id=str(task.id),
                message_id=message_id,
                priority=priority.value,
            )

            return message_id

        except Exception as e:
            logger.error(
                "notification_failed",
                task_id=str(task.id),
                error=str(e),
            )
            raise NotificationError(f"Failed to send notification: {e}")

    async def should_notify(self, task: Task) -> bool:
        """Check if task should trigger a notification."""
        try:
            priority = TaskPriority(task.priority)
            return priority in self.NOTIFY_PRIORITIES
        except ValueError:
            return False

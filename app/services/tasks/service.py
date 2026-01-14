"""Task generation service."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import SUBCATEGORY_TO_MAIN, SubCategory, TaskStatus
from app.core.exceptions import TaskCreationError
from app.core.logging import get_logger
from app.db.models.contact import Contact
from app.db.models.task import Task
from app.services.tasks.factory import TaskFactory

logger = get_logger(__name__)


class TaskService:
    """Service for generating and managing tasks."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.factory = TaskFactory()

    async def create_tasks_for_reply(
        self,
        contact: Contact,
        subcategory: SubCategory,
        reply_id: UUID | None = None,
    ) -> list[Task]:
        """
        Create HubSpot tasks based on email reply categorization.

        Args:
            contact: The contact who replied
            subcategory: Categorization subcategory
            reply_id: ID of the email reply that triggered this

        Returns:
            List of created Task objects
        """
        try:
            # Generate task definitions
            task_definitions = self.factory.create_tasks_for_category(
                subcategory=subcategory,
                contact_name=contact.full_name,
                company_name=contact.company_name,
            )

            if not task_definitions:
                logger.info(
                    "no_tasks_for_category",
                    contact_id=str(contact.id),
                    subcategory=subcategory.value,
                )
                return []

            # Create task records
            # Get main category from subcategory mapping
            main_category = SUBCATEGORY_TO_MAIN.get(subcategory)

            tasks = []
            for task_def in task_definitions:
                task = Task(
                    contact_id=contact.id,
                    title=task_def.title,
                    description=task_def.description,
                    priority=task_def.priority.value,
                    category=main_category.value if main_category else None,
                    subcategory=subcategory.value,
                    task_type=task_def.task_type,
                    due_date=task_def.due_date,
                    sync_status=TaskStatus.PENDING.value,
                    triggered_by_reply_id=reply_id,
                )
                self.session.add(task)
                tasks.append(task)

            await self.session.flush()

            logger.info(
                "tasks_created",
                contact_id=str(contact.id),
                subcategory=subcategory.value,
                task_count=len(tasks),
            )

            return tasks

        except Exception as e:
            logger.error(
                "task_creation_failed",
                contact_id=str(contact.id),
                error=str(e),
            )
            raise TaskCreationError(f"Failed to create tasks: {e}")

    async def get_pending_tasks(self, limit: int = 100) -> list[Task]:
        """Get tasks pending HubSpot sync."""
        from sqlalchemy import select

        stmt = (
            select(Task)
            .where(Task.sync_status == TaskStatus.PENDING.value)
            .order_by(Task.created_at)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

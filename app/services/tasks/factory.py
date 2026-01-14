"""Task factory for generating HubSpot tasks by category."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.core.constants import SubCategory, TaskPriority, TASK_TYPES


@dataclass
class TaskDefinition:
    """Definition for a task to be created."""

    title: str
    priority: TaskPriority
    task_type: str
    due_date: datetime
    description: str | None = None


class TaskFactory:
    """Factory for creating task definitions based on category."""

    # Due date offsets by priority
    DUE_DATE_HOURS: dict[TaskPriority, int] = {
        TaskPriority.HIGHEST: 12,
        TaskPriority.HIGH: 24,
        TaskPriority.MEDIUM: 48,
        TaskPriority.LOW: 168,  # 1 week
    }

    def create_tasks_for_category(
        self,
        subcategory: SubCategory,
        contact_name: str,
        company_name: str,
    ) -> list[TaskDefinition]:
        """
        Create task definitions for a given subcategory.

        Args:
            subcategory: The categorization subcategory
            contact_name: Name of the contact
            company_name: Name of the company

        Returns:
            List of TaskDefinition objects to be created
        """
        task_configs = TASK_TYPES.get(subcategory, [])
        tasks = []

        for title_template, priority in task_configs:
            title = f"{title_template}: {contact_name} - {company_name}"
            due_date = self._calculate_due_date(priority)

            tasks.append(
                TaskDefinition(
                    title=title,
                    priority=priority,
                    task_type=title_template.lower().replace(" ", "_"),
                    due_date=due_date,
                    description=f"Auto-generated task for {subcategory.value} response",
                )
            )

        return tasks

    def _calculate_due_date(self, priority: TaskPriority) -> datetime:
        """Calculate due date based on priority."""
        hours = self.DUE_DATE_HOURS.get(priority, 48)
        return datetime.utcnow() + timedelta(hours=hours)

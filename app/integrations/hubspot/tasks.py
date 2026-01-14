"""HubSpot Tasks API."""

from datetime import datetime
from typing import Any

from app.core.constants import TaskPriority
from app.core.exceptions import HubSpotError
from app.core.logging import get_logger
from app.integrations.hubspot.client import HubSpotClient

logger = get_logger(__name__)


# HubSpot priority mapping
HUBSPOT_PRIORITY_MAP = {
    TaskPriority.HIGHEST: "HIGH",
    TaskPriority.HIGH: "HIGH",
    TaskPriority.MEDIUM: "MEDIUM",
    TaskPriority.LOW: "LOW",
}


class HubSpotTasks:
    """HubSpot Tasks API wrapper."""

    def __init__(self, client: HubSpotClient | None = None):
        self.client = client or HubSpotClient()

    async def create_task(
        self,
        title: str,
        due_date: datetime,
        priority: TaskPriority,
        contact_id: str | None = None,
        description: str | None = None,
        assigned_to: str | None = None,
    ) -> dict[str, Any]:
        """Create a new task in HubSpot."""
        try:
            # Convert priority
            hs_priority = HUBSPOT_PRIORITY_MAP.get(priority, "MEDIUM")

            # Build payload
            payload: dict[str, Any] = {
                "properties": {
                    "hs_task_subject": title,
                    "hs_task_body": description or "",
                    "hs_task_priority": hs_priority,
                    "hs_task_status": "NOT_STARTED",
                    "hs_task_due_date": int(due_date.timestamp() * 1000),
                }
            }

            # Add owner if specified
            if assigned_to:
                payload["properties"]["hubspot_owner_id"] = assigned_to

            # Create task
            response = await self.client.post(
                "/crm/v3/objects/tasks",
                json=payload,
            )

            task_id = response.get("id")

            # Associate with contact if provided
            if contact_id and task_id:
                await self._associate_task_with_contact(task_id, contact_id)

            logger.info(
                "hubspot_task_created",
                task_id=task_id,
                title=title,
                contact_id=contact_id,
            )

            return response

        except Exception as e:
            raise HubSpotError(f"Failed to create task: {e}")

    async def _associate_task_with_contact(
        self,
        task_id: str,
        contact_id: str,
    ) -> None:
        """Associate a task with a contact."""
        try:
            # HubSpot v3 associations API: use association type ID (204 = task to contact)
            await self.client.put(
                f"/crm/v3/objects/tasks/{task_id}/associations/contacts/{contact_id}/204",
                json={},
            )
        except Exception as e:
            logger.warning(
                "task_association_failed",
                task_id=task_id,
                contact_id=contact_id,
                error=str(e),
            )

    async def get_task(self, task_id: str) -> dict[str, Any]:
        """Get task by ID."""
        try:
            return await self.client.get(f"/crm/v3/objects/tasks/{task_id}")
        except Exception as e:
            raise HubSpotError(f"Failed to get task {task_id}: {e}")

    async def update_task_status(
        self,
        task_id: str,
        status: str,
    ) -> dict[str, Any]:
        """Update task status (NOT_STARTED, IN_PROGRESS, COMPLETED)."""
        try:
            return await self.client.patch(
                f"/crm/v3/objects/tasks/{task_id}",
                json={"properties": {"hs_task_status": status}},
            )
        except Exception as e:
            raise HubSpotError(f"Failed to update task {task_id}: {e}")

    def get_task_url(self, task_id: str) -> str:
        """Get direct URL to task in HubSpot."""
        return f"https://app.hubspot.com/tasks/{task_id}"

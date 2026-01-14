"""LinkedIn approval workflow service.

All LinkedIn messages require human approval before sending.
This service creates pending messages and approval tasks.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    LinkedInMessageStatus,
    LinkedInMessageType,
    TaskPriority,
    TaskStatus,
)
from app.core.logging import get_logger
from app.db.models.contact import Contact
from app.db.models.linkedin_message import PendingLinkedInMessage
from app.db.models.task import Task

logger = get_logger(__name__)


class LinkedInApprovalService:
    """Service for LinkedIn message approval workflow."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def queue_connection_request(
        self,
        contact: Contact,
        profile_url: str,
        message: str | None = None,
        context: str | None = None,
    ) -> tuple[PendingLinkedInMessage, Task]:
        """
        Queue a LinkedIn connection request for human approval.

        Instead of sending directly, creates:
        1. A PendingLinkedInMessage record
        2. A HubSpot task for approval

        Args:
            contact: The contact to connect with
            profile_url: LinkedIn profile URL
            message: Optional connection note
            context: Why this message is being sent (for reviewer context)

        Returns:
            Tuple of (pending_message, approval_task)
        """
        # Create pending message
        pending_message = PendingLinkedInMessage(
            contact_id=contact.id,
            message_type=LinkedInMessageType.CONNECTION_REQUEST.value,
            profile_url=profile_url,
            message_content=message,
            status=LinkedInMessageStatus.PENDING_APPROVAL.value,
            context=context,
        )
        self.session.add(pending_message)
        await self.session.flush()

        # Create approval task
        task = Task(
            contact_id=contact.id,
            title=f"Approve LinkedIn Connection: {contact.full_name}",
            description=self._build_approval_description(
                message_type="Connection Request",
                contact=contact,
                profile_url=profile_url,
                message=message,
                context=context,
            ),
            priority=TaskPriority.HIGH.value,
            category="linkedin_approval",
            task_type="LinkedIn Connection Approval",
            due_date=datetime.now(timezone.utc) + timedelta(hours=24),
            sync_status=TaskStatus.PENDING.value,
        )
        self.session.add(task)
        await self.session.flush()

        # Link task to pending message
        pending_message.approval_task_id = task.id
        await self.session.flush()

        logger.info(
            "linkedin_connection_queued",
            contact_id=str(contact.id),
            profile_url=profile_url,
            pending_message_id=str(pending_message.id),
            approval_task_id=str(task.id),
        )

        return pending_message, task

    async def queue_direct_message(
        self,
        contact: Contact,
        profile_url: str,
        message: str,
        context: str | None = None,
    ) -> tuple[PendingLinkedInMessage, Task]:
        """
        Queue a LinkedIn direct message for human approval.

        Args:
            contact: The contact to message
            profile_url: LinkedIn profile URL
            message: Message content
            context: Why this message is being sent

        Returns:
            Tuple of (pending_message, approval_task)
        """
        # Create pending message
        pending_message = PendingLinkedInMessage(
            contact_id=contact.id,
            message_type=LinkedInMessageType.DIRECT_MESSAGE.value,
            profile_url=profile_url,
            message_content=message,
            status=LinkedInMessageStatus.PENDING_APPROVAL.value,
            context=context,
        )
        self.session.add(pending_message)
        await self.session.flush()

        # Create approval task
        task = Task(
            contact_id=contact.id,
            title=f"Approve LinkedIn DM: {contact.full_name}",
            description=self._build_approval_description(
                message_type="Direct Message",
                contact=contact,
                profile_url=profile_url,
                message=message,
                context=context,
            ),
            priority=TaskPriority.HIGH.value,
            category="linkedin_approval",
            task_type="LinkedIn DM Approval",
            due_date=datetime.now(timezone.utc) + timedelta(hours=24),
            sync_status=TaskStatus.PENDING.value,
        )
        self.session.add(task)
        await self.session.flush()

        # Link task to pending message
        pending_message.approval_task_id = task.id
        await self.session.flush()

        logger.info(
            "linkedin_dm_queued",
            contact_id=str(contact.id),
            profile_url=profile_url,
            pending_message_id=str(pending_message.id),
            approval_task_id=str(task.id),
        )

        return pending_message, task

    async def approve_message(
        self,
        message_id: UUID,
        approved_by: str | None = None,
    ) -> PendingLinkedInMessage:
        """Mark a pending message as approved."""
        stmt = select(PendingLinkedInMessage).where(PendingLinkedInMessage.id == message_id)
        result = await self.session.execute(stmt)
        message = result.scalar_one_or_none()

        if not message:
            raise ValueError(f"Message {message_id} not found")

        message.status = LinkedInMessageStatus.APPROVED.value
        message.approved_at = datetime.now(timezone.utc)
        message.approved_by = approved_by
        await self.session.flush()

        logger.info(
            "linkedin_message_approved",
            message_id=str(message_id),
            approved_by=approved_by,
        )

        return message

    async def reject_message(
        self,
        message_id: UUID,
        reason: str | None = None,
    ) -> PendingLinkedInMessage:
        """Mark a pending message as rejected."""
        stmt = select(PendingLinkedInMessage).where(PendingLinkedInMessage.id == message_id)
        result = await self.session.execute(stmt)
        message = result.scalar_one_or_none()

        if not message:
            raise ValueError(f"Message {message_id} not found")

        message.status = LinkedInMessageStatus.REJECTED.value
        message.rejection_reason = reason
        await self.session.flush()

        logger.info(
            "linkedin_message_rejected",
            message_id=str(message_id),
            reason=reason,
        )

        return message

    async def get_approved_messages(self, limit: int = 50) -> list[PendingLinkedInMessage]:
        """Get messages approved and ready to send."""
        stmt = (
            select(PendingLinkedInMessage)
            .where(PendingLinkedInMessage.status == LinkedInMessageStatus.APPROVED.value)
            .order_by(PendingLinkedInMessage.approved_at)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_as_sent(
        self,
        message_id: UUID,
    ) -> PendingLinkedInMessage:
        """Mark a message as successfully sent."""
        stmt = select(PendingLinkedInMessage).where(PendingLinkedInMessage.id == message_id)
        result = await self.session.execute(stmt)
        message = result.scalar_one_or_none()

        if not message:
            raise ValueError(f"Message {message_id} not found")

        message.status = LinkedInMessageStatus.SENT.value
        message.sent_at = datetime.now(timezone.utc)
        await self.session.flush()

        return message

    async def mark_as_failed(
        self,
        message_id: UUID,
        error: str,
    ) -> PendingLinkedInMessage:
        """Mark a message as failed to send."""
        stmt = select(PendingLinkedInMessage).where(PendingLinkedInMessage.id == message_id)
        result = await self.session.execute(stmt)
        message = result.scalar_one_or_none()

        if not message:
            raise ValueError(f"Message {message_id} not found")

        message.status = LinkedInMessageStatus.FAILED.value
        message.send_error = error
        await self.session.flush()

        logger.error(
            "linkedin_message_send_failed",
            message_id=str(message_id),
            error=error,
        )

        return message

    def _build_approval_description(
        self,
        message_type: str,
        contact: Contact,
        profile_url: str,
        message: str | None,
        context: str | None,
    ) -> str:
        """Build detailed description for approval task."""
        lines = [
            f"**{message_type} Approval Required**",
            "",
            f"**Contact:** {contact.full_name}",
            f"**Company:** {contact.company_name}",
            f"**Email:** {contact.email}",
            f"**LinkedIn:** {profile_url}",
        ]

        if message:
            lines.extend([
                "",
                "**Message to Send:**",
                message,
            ])

        if context:
            lines.extend([
                "",
                "**Context:**",
                context,
            ])

        lines.extend([
            "",
            "---",
            "Complete this task to APPROVE the message.",
            "Delete this task to REJECT the message.",
        ])

        return "\n".join(lines)

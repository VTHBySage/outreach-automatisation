"""Pending LinkedIn message model for approval workflow."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import LinkedInMessageStatus, LinkedInMessageType
from app.db.base import Base, TimestampMixin, UUIDMixin


class PendingLinkedInMessage(Base, UUIDMixin, TimestampMixin):
    """
    Pending LinkedIn messages awaiting human approval.

    All LinkedIn messages require human approval before sending.
    This model stores the message until approved via HubSpot task completion.
    """

    __tablename__ = "pending_linkedin_messages"

    # Relationships
    contact_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    contact: Mapped["Contact"] = relationship("Contact", back_populates="pending_linkedin_messages")

    # Associated approval task
    approval_task_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Message details
    message_type: Mapped[str] = mapped_column(
        String(50),
        default=LinkedInMessageType.DIRECT_MESSAGE.value,
        nullable=False,
    )
    profile_url: Mapped[str] = mapped_column(String(500), nullable=False)
    message_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(30),
        default=LinkedInMessageStatus.PENDING_APPROVAL.value,
        index=True,
        nullable=False,
    )

    # Approval tracking
    approved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Execution tracking
    sent_at: Mapped[datetime | None] = mapped_column(nullable=True)
    send_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Context for the message (e.g., why it's being sent)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index(
            "ix_pending_linkedin_messages_approved",
            "status",
            postgresql_where=f"status = '{LinkedInMessageStatus.APPROVED.value}'",
        ),
    )


# Import for type hints
from app.db.models.contact import Contact  # noqa: E402

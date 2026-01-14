"""Task model for HubSpot task tracking."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import TaskPriority, TaskStatus
from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class Task(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """HubSpot task tracking model."""

    __tablename__ = "tasks"

    # Relationships
    contact_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    contact: Mapped["Contact"] = relationship("Contact", back_populates="tasks")

    # Task definition
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(
        String(20),
        default=TaskPriority.MEDIUM.value,
        index=True,
        nullable=False,
    )
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    subcategory: Mapped[str | None] = mapped_column(String(50), nullable=True)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # Assignment
    assigned_to: Mapped[str | None] = mapped_column(String(100), nullable=True)
    due_date: Mapped[datetime] = mapped_column(index=True, nullable=False)

    # HubSpot sync
    hubspot_task_id: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    sync_status: Mapped[str] = mapped_column(
        String(20),
        default=TaskStatus.PENDING.value,
        nullable=False,
    )
    synced_at: Mapped[datetime | None] = mapped_column(nullable=True)
    sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # MS Teams notification
    ms_teams_message_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notification_sent_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Metadata
    triggered_by_reply_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("email_replies.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Completion
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        Index("ix_tasks_pending_by_priority", "priority", "due_date", postgresql_where="sync_status = 'pending'"),
    )


# Import for type hints
from app.db.models.contact import Contact  # noqa: E402

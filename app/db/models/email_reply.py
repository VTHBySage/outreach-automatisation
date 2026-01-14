"""Email reply model with categorization tracking."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import WebhookSource
from app.db.base import Base, TimestampMixin, UUIDMixin


class EmailReply(Base, UUIDMixin, TimestampMixin):
    """Email reply with AI categorization history."""

    __tablename__ = "email_replies"

    # Relationships
    contact_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    contact: Mapped["Contact"] = relationship("Contact", back_populates="email_replies")

    # Source info
    source: Mapped[str] = mapped_column(
        String(50),
        default=WebhookSource.SMARTLEAD.value,
        nullable=False,
    )
    external_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    campaign_external_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Content
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(nullable=False)

    # Email thread context
    thread_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    in_reply_to: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Categorization
    main_category: Mapped[str | None] = mapped_column(String(50), index=True, nullable=True)
    subcategory: Mapped[str | None] = mapped_column(String(50), index=True, nullable=True)
    categorization_confidence: Mapped[Decimal | None] = mapped_column(nullable=True)
    categorization_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    categorized_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Processing status
    processed: Mapped[bool] = mapped_column(default=False, nullable=False)
    tasks_created: Mapped[bool] = mapped_column(default=False, nullable=False)
    notification_sent: Mapped[bool] = mapped_column(default=False, nullable=False)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_email_replies_unprocessed", "processed", postgresql_where="processed = false"),
        Index("ix_email_replies_source_external", "source", "external_id", unique=True),
    )


# Import for type hints
from app.db.models.contact import Contact  # noqa: E402

"""Contact model."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import LeadSource, ValidationStatus
from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class Contact(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Contact/Lead model."""

    __tablename__ = "contacts"

    # Primary fields
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Company info
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_domain: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    company_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Validation fields
    validation_status: Mapped[str] = mapped_column(
        String(20),
        default=ValidationStatus.PENDING.value,
        nullable=False,
    )
    validation_confidence: Mapped[Decimal | None] = mapped_column(nullable=True)
    validation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Campaign tracking
    campaign_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), index=True, nullable=True)
    source: Mapped[str] = mapped_column(
        String(50),
        default=LeadSource.MANUAL.value,
        nullable=False,
    )

    # Re-engagement
    re_engagement_date: Mapped[datetime | None] = mapped_column(index=True, nullable=True)
    re_engagement_category: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Status
    last_contacted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_response_at: Mapped[datetime | None] = mapped_column(nullable=True)
    current_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    current_subcategory: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Channel switching (Email → LinkedIn → Phone)
    current_channel: Mapped[str] = mapped_column(
        String(20),
        default="email",
        nullable=False,
    )
    channel_switched_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_engagement_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # External IDs
    hubspot_contact_id: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    apollo_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    smartlead_lead_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="contact")
    email_replies: Mapped[list["EmailReply"]] = relationship("EmailReply", back_populates="contact")
    pending_linkedin_messages: Mapped[list["PendingLinkedInMessage"]] = relationship(
        "PendingLinkedInMessage", back_populates="contact"
    )

    __table_args__ = (
        Index("ix_contacts_company_domain_not_deleted", "company_domain", postgresql_where="deleted_at IS NULL"),
        Index("ix_contacts_re_engagement", "re_engagement_date", postgresql_where="deleted_at IS NULL"),
    )

    @property
    def full_name(self) -> str:
        """Get full name."""
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p) or self.email


# Import for type hints
from app.db.models.email_reply import EmailReply  # noqa: E402
from app.db.models.linkedin_message import PendingLinkedInMessage  # noqa: E402
from app.db.models.task import Task  # noqa: E402

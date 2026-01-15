"""Campaign model with targeting criteria for LLM validation."""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.db.models.contact import Contact


class Campaign(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Campaign with configurable targeting criteria for LLM company validation.

    This model stores campaign settings including:
    - SmartLead campaign reference
    - Target company types and industries
    - Employee size filters
    - Validation confidence thresholds
    """

    __tablename__ = "campaigns"

    # SmartLead reference
    smartlead_campaign_id: Mapped[int | None] = mapped_column(
        Integer,
        unique=True,
        index=True,
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        default="active",
        nullable=False,
    )

    # Target Criteria (stored as JSON arrays)
    target_types: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Target company types, e.g., ['hotel_chain', 'resort', 'boutique_hotel']",
    )
    target_industries: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Target industries, e.g., ['hospitality', 'travel']",
    )
    exclude_types: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Company types to exclude, e.g., ['airbnb', 'vacation_rental']",
    )

    # Employee size filters
    min_employees: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_employees: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Validation thresholds
    min_confidence: Mapped[Decimal] = mapped_column(
        default=Decimal("0.85"),
        nullable=False,
        comment="Minimum confidence for auto-approval (85%)",
    )
    review_threshold: Mapped[Decimal] = mapped_column(
        default=Decimal("0.75"),
        nullable=False,
        comment="Threshold for manual review queue (75-85%)",
    )

    # Custom validation prompt (optional)
    validation_prompt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional custom prompt for LLM validation",
    )

    # ROI Tracking fields
    cost_per_email: Mapped[Decimal | None] = mapped_column(
        default=Decimal("0.05"),
        nullable=True,
        comment="Cost per email sent (default $0.05 for SmartLead)",
    )
    average_deal_value: Mapped[Decimal | None] = mapped_column(
        default=Decimal("5000.00"),
        nullable=True,
        comment="Average deal value for conversion tracking",
    )
    total_emails_sent: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total emails sent in this campaign",
    )

    # Relationships
    contacts: Mapped[list["Contact"]] = relationship(
        "Contact",
        back_populates="campaign",
        foreign_keys="Contact.campaign_id",
    )

    def get_criteria_dict(self) -> dict:
        """Get campaign criteria as a dictionary for LLM validation."""
        return {
            "target_types": self.target_types or [],
            "industries": self.target_industries or [],
            "exclude_types": self.exclude_types or [],
            "min_employees": self.min_employees,
            "max_employees": self.max_employees,
        }

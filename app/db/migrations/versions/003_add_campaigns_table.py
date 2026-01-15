"""Add campaigns table for LLM company validation.

Revision ID: 003
Revises: 002
Create Date: 2026-01-15

Creates campaigns table with:
- SmartLead integration
- Target criteria (types, industries, employee size)
- Validation confidence thresholds
- Contact FK relationship
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create campaigns table
    op.create_table(
        "campaigns",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # SmartLead reference
        sa.Column("smartlead_campaign_id", sa.Integer(), unique=True, nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        # Target criteria (JSON arrays)
        sa.Column("target_types", JSONB(), nullable=True, comment="Target company types, e.g., ['hotel_chain', 'resort']"),
        sa.Column("target_industries", JSONB(), nullable=True, comment="Target industries, e.g., ['hospitality', 'travel']"),
        sa.Column("exclude_types", JSONB(), nullable=True, comment="Company types to exclude"),
        # Employee size filters
        sa.Column("min_employees", sa.Integer(), nullable=True),
        sa.Column("max_employees", sa.Integer(), nullable=True),
        # Validation thresholds
        sa.Column("min_confidence", sa.Numeric(3, 2), nullable=False, server_default="0.85"),
        sa.Column("review_threshold", sa.Numeric(3, 2), nullable=False, server_default="0.75"),
        # Custom validation prompt
        sa.Column("validation_prompt", sa.Text(), nullable=True),
    )

    # Create indexes
    op.create_index("ix_campaigns_smartlead_id", "campaigns", ["smartlead_campaign_id"])
    op.create_index("ix_campaigns_status", "campaigns", ["status"], postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_index("ix_campaigns_name", "campaigns", ["name"], postgresql_where=sa.text("deleted_at IS NULL"))

    # Add foreign key constraint to contacts.campaign_id
    # Note: campaign_id column already exists, we just add the FK constraint
    op.create_foreign_key(
        "fk_contacts_campaign_id",
        "contacts",
        "campaigns",
        ["campaign_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # Drop foreign key constraint
    op.drop_constraint("fk_contacts_campaign_id", "contacts", type_="foreignkey")

    # Drop indexes
    op.drop_index("ix_campaigns_name", table_name="campaigns")
    op.drop_index("ix_campaigns_status", table_name="campaigns")
    op.drop_index("ix_campaigns_smartlead_id", table_name="campaigns")

    # Drop campaigns table
    op.drop_table("campaigns")

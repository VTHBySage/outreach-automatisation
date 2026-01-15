"""Add ROI tracking fields to campaigns table.

Revision ID: 004
Revises: 003
Create Date: 2026-01-15

Adds cost and ROI tracking fields to campaigns:
- cost_per_email: Cost per email sent (default $0.05)
- average_deal_value: Average deal value for ROI calculation
- total_emails_sent: Counter for emails sent in campaign
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add ROI tracking columns to campaigns table
    op.add_column(
        "campaigns",
        sa.Column(
            "cost_per_email",
            sa.Numeric(10, 4),
            nullable=True,
            server_default="0.05",
            comment="Cost per email sent (default $0.05 for SmartLead)",
        ),
    )
    op.add_column(
        "campaigns",
        sa.Column(
            "average_deal_value",
            sa.Numeric(12, 2),
            nullable=True,
            server_default="5000.00",
            comment="Average deal value for conversion tracking",
        ),
    )
    op.add_column(
        "campaigns",
        sa.Column(
            "total_emails_sent",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Total emails sent in this campaign",
        ),
    )


def downgrade() -> None:
    # Remove ROI tracking columns
    op.drop_column("campaigns", "total_emails_sent")
    op.drop_column("campaigns", "average_deal_value")
    op.drop_column("campaigns", "cost_per_email")

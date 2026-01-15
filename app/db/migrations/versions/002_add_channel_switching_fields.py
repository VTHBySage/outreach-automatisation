"""Add channel switching fields to contacts.

Revision ID: 002
Revises: 001
Create Date: 2026-01-15

Adds fields for multi-channel orchestration:
- current_channel: email, linkedin, phone
- channel_switched_at: timestamp of last channel switch
- last_engagement_at: timestamp of last engagement
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add channel switching fields to contacts table
    op.add_column(
        "contacts",
        sa.Column(
            "current_channel",
            sa.String(20),
            nullable=False,
            server_default="email",
        ),
    )
    op.add_column(
        "contacts",
        sa.Column("channel_switched_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "contacts",
        sa.Column("last_engagement_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Add index for channel-based queries
    op.create_index(
        "ix_contacts_current_channel",
        "contacts",
        ["current_channel"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_contacts_current_channel", table_name="contacts")
    op.drop_column("contacts", "last_engagement_at")
    op.drop_column("contacts", "channel_switched_at")
    op.drop_column("contacts", "current_channel")

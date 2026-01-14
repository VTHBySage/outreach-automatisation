"""Initial database schema.

Revision ID: 001
Revises:
Create Date: 2026-01-12

Creates tables:
- contacts
- email_replies
- tasks
- webhook_logs
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### contacts table ###
    op.create_table(
        "contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=True),
        sa.Column("last_name", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("linkedin_url", sa.String(500), nullable=True),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("company_domain", sa.String(255), nullable=True),
        sa.Column("company_type", sa.String(100), nullable=True),
        sa.Column("validation_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("validation_confidence", sa.Numeric(), nullable=True),
        sa.Column("validation_notes", sa.Text(), nullable=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source", sa.String(50), nullable=False, server_default="manual"),
        sa.Column("re_engagement_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("re_engagement_category", sa.String(50), nullable=True),
        sa.Column("last_contacted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_response_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_category", sa.String(50), nullable=True),
        sa.Column("current_subcategory", sa.String(50), nullable=True),
        sa.Column("hubspot_contact_id", sa.String(50), nullable=True),
        sa.Column("apollo_id", sa.String(50), nullable=True),
        sa.Column("smartlead_lead_id", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("hubspot_contact_id"),
    )
    op.create_index("ix_contacts_email", "contacts", ["email"], unique=True)
    op.create_index("ix_contacts_company_domain", "contacts", ["company_domain"], unique=False)
    op.create_index("ix_contacts_campaign_id", "contacts", ["campaign_id"], unique=False)
    op.create_index("ix_contacts_re_engagement_date", "contacts", ["re_engagement_date"], unique=False)
    op.create_index(
        "ix_contacts_company_domain_not_deleted",
        "contacts",
        ["company_domain"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_contacts_re_engagement",
        "contacts",
        ["re_engagement_date"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ### email_replies table ###
    op.create_table(
        "email_replies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(50), nullable=False, server_default="smartlead"),
        sa.Column("external_id", sa.String(100), nullable=False),
        sa.Column("campaign_external_id", sa.String(100), nullable=True),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("thread_id", sa.String(100), nullable=True),
        sa.Column("in_reply_to", sa.String(100), nullable=True),
        sa.Column("main_category", sa.String(50), nullable=True),
        sa.Column("subcategory", sa.String(50), nullable=True),
        sa.Column("categorization_confidence", sa.Numeric(), nullable=True),
        sa.Column("categorization_reasoning", sa.Text(), nullable=True),
        sa.Column("categorized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("tasks_created", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("notification_sent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_replies_contact_id", "email_replies", ["contact_id"], unique=False)
    op.create_index("ix_email_replies_external_id", "email_replies", ["external_id"], unique=False)
    op.create_index("ix_email_replies_main_category", "email_replies", ["main_category"], unique=False)
    op.create_index("ix_email_replies_subcategory", "email_replies", ["subcategory"], unique=False)
    op.create_index(
        "ix_email_replies_unprocessed",
        "email_replies",
        ["processed"],
        unique=False,
        postgresql_where=sa.text("processed = false"),
    )
    op.create_index(
        "ix_email_replies_source_external",
        "email_replies",
        ["source", "external_id"],
        unique=True,
    )

    # ### tasks table ###
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("subcategory", sa.String(50), nullable=True),
        sa.Column("task_type", sa.String(100), nullable=False),
        sa.Column("assigned_to", sa.String(100), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hubspot_task_id", sa.String(50), nullable=True),
        sa.Column("sync_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_error", sa.Text(), nullable=True),
        sa.Column("ms_teams_message_id", sa.String(100), nullable=True),
        sa.Column("notification_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("triggered_by_reply_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["triggered_by_reply_id"], ["email_replies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hubspot_task_id"),
    )
    op.create_index("ix_tasks_contact_id", "tasks", ["contact_id"], unique=False)
    op.create_index("ix_tasks_priority", "tasks", ["priority"], unique=False)
    op.create_index("ix_tasks_due_date", "tasks", ["due_date"], unique=False)
    op.create_index(
        "ix_tasks_pending_by_priority",
        "tasks",
        ["priority", "due_date"],
        unique=False,
        postgresql_where=sa.text("sync_status = 'pending'"),
    )

    # ### webhook_logs table ###
    op.create_table(
        "webhook_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("endpoint", sa.String(255), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("headers", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("processed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("response_status", sa.Integer(), nullable=False),
        sa.Column("response_body", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_webhook_logs_source", "webhook_logs", ["source"], unique=False)
    op.create_index("ix_webhook_logs_received_at", "webhook_logs", ["received_at"], unique=False)
    op.create_index(
        "ix_webhook_logs_recent",
        "webhook_logs",
        ["received_at"],
        unique=False,
        postgresql_using="btree",
    )


def downgrade() -> None:
    # ### Drop tables in reverse order (respecting FKs) ###
    op.drop_table("webhook_logs")
    op.drop_table("tasks")
    op.drop_table("email_replies")
    op.drop_table("contacts")

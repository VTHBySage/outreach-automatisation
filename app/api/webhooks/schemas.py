"""Webhook payload schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class LeadCorrespondence(BaseModel):
    """SmartLead lead correspondence tracking."""

    targetLeadEmail: str | None = Field(None, description="Original campaign recipient")
    replyReceivedFrom: str | None = Field(None, description="Actual responder's email")
    repliedCompanyDomain: str | None = Field(
        None, description="SameCompany, DifferentCompany, or Unknown"
    )


class SmartLeadWebhookPayload(BaseModel):
    """
    SmartLead webhook payload schema.

    Based on official SmartLead API documentation:
    https://api.smartlead.ai/reference/email-reply-webhooks
    """

    # Event identification
    event_type: str | None = Field(None, description="Type of webhook event (e.g., EMAIL_REPLY)")

    # Campaign info
    campaign_id: int | None = Field(None, description="SmartLead campaign ID")
    campaign_name: str | None = Field(None, description="Campaign name")
    campaign_status: str | None = Field(None, description="Current campaign status")
    sequence_number: int | None = Field(None, description="Which email in sequence was replied to")

    # Lead identification (SmartLead uses 'sl_' prefix)
    sl_email_lead_id: str | None = Field(None, description="SmartLead internal lead ID")
    sl_email_lead_map_id: int | None = Field(None, description="Campaign-to-lead mapping ID")
    sl_lead_email: str | None = Field(None, description="Lead's email address")
    stats_id: str | None = Field(None, description="Stats tracking ID")

    # Email details
    from_email: str | None = Field(None, description="Email that sent the original")
    to_email: str | None = Field(None, description="Recipient email")
    to_name: str | None = Field(None, description="Recipient name")
    cc_emails: list[str] | None = Field(None, description="CC recipients")
    subject: str | None = Field(None, description="Email subject")
    preview_text: str | None = Field(None, description="Preview of reply content")
    message_id: str | None = Field(None, description="Unique email message ID")

    # Timestamps
    time_replied: datetime | None = Field(None, description="When the reply was received")
    event_timestamp: datetime | None = Field(None, description="Event timestamp")

    # Webhook metadata
    secret_key: str | None = Field(None, description="Webhook secret for verification")
    webhook_id: str | None = Field(None, description="Webhook configuration ID")
    webhook_name: str | None = Field(None, description="Webhook name")
    webhook_url: str | None = Field(None, description="Webhook target URL")
    description: str | None = Field(None, description="Event description")

    # URLs
    app_url: str | None = Field(None, description="Link to view in SmartLead app")
    ui_master_inbox_link: str | None = Field(None, description="Link to master inbox")

    # Enhanced tracking
    leadCorrespondence: LeadCorrespondence | None = Field(
        None, description="Lead correspondence tracking"
    )
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")

    class Config:
        extra = "allow"  # Allow additional fields from SmartLead

    # Backward compatibility properties
    @property
    def lead_id(self) -> str | None:
        """Backward compatible lead_id accessor."""
        return self.sl_email_lead_id

    @property
    def email(self) -> str | None:
        """Backward compatible email accessor."""
        return self.sl_lead_email

    @property
    def reply_text(self) -> str | None:
        """Backward compatible reply_text accessor."""
        return self.preview_text

    @property
    def received_at(self) -> datetime | None:
        """Backward compatible received_at accessor."""
        return self.time_replied or self.event_timestamp

    @property
    def thread_id(self) -> str | None:
        """Backward compatible thread_id accessor."""
        return self.message_id


class ConnectSafelyWebhookPayload(BaseModel):
    """ConnectSafely webhook payload schema."""

    event_type: str = Field(..., description="Type of webhook event")
    profile_url: str | None = Field(None, description="LinkedIn profile URL")
    email: str | None = Field(None, description="Associated email address")
    message_text: str | None = Field(None, description="LinkedIn message content")
    connection_status: str | None = Field(None, description="Connection request status")
    received_at: datetime | None = Field(None, description="When the event occurred")

    class Config:
        extra = "allow"  # Allow additional fields from ConnectSafely


class WebhookResponse(BaseModel):
    """Standard webhook response."""

    status: str = "received"
    message: str = "Webhook queued for processing"
    webhook_id: str | None = None

"""API v1 request/response schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# === Contact Schemas ===

class ContactBase(BaseModel):
    """Base contact fields."""

    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    company_name: str
    company_domain: str | None = None


class ContactCreate(ContactBase):
    """Create contact request."""

    pass


class ContactUpdate(BaseModel):
    """Update contact request (all fields optional)."""

    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    company_name: str | None = None
    company_domain: str | None = None
    linkedin_url: str | None = None
    current_category: str | None = None
    current_subcategory: str | None = None


class ContactResponse(ContactBase):
    """Contact response schema."""

    id: UUID
    linkedin_url: str | None = None
    company_type: str | None = None
    validation_status: str
    validation_confidence: Decimal | None = Field(None, ge=0, le=1)
    source: str
    current_category: str | None = None
    current_subcategory: str | None = None
    last_contacted_at: datetime | None = None
    last_response_at: datetime | None = None
    re_engagement_date: datetime | None = None
    hubspot_contact_id: str | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("validation_confidence")
    @classmethod
    def validate_confidence_range(cls, v: Decimal | None) -> Decimal | None:
        """Validate confidence is between 0 and 1."""
        if v is not None and (v < 0 or v > 1):
            raise ValueError("validation_confidence must be between 0 and 1")
        return v

    class Config:
        from_attributes = True


class ContactListResponse(BaseModel):
    """Paginated contact list response."""

    items: list[ContactResponse]
    total: int
    page: int
    page_size: int
    pages: int


# Valid priority values
VALID_PRIORITIES = {"highest", "high", "medium", "low"}


# === Task Schemas ===

class TaskBase(BaseModel):
    """Base task fields."""

    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    priority: str
    task_type: str = Field(..., min_length=1, max_length=100)
    due_date: datetime

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        """Validate priority is a valid value."""
        if v.lower() not in VALID_PRIORITIES:
            raise ValueError(f"priority must be one of: {', '.join(VALID_PRIORITIES)}")
        return v.lower()


class TaskCreate(TaskBase):
    """Create task request."""

    contact_id: UUID


class TaskUpdate(BaseModel):
    """Update task request (all fields optional)."""

    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    priority: str | None = None
    assigned_to: str | None = None
    due_date: datetime | None = None

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str | None) -> str | None:
        """Validate priority is a valid value."""
        if v is not None and v.lower() not in VALID_PRIORITIES:
            raise ValueError(f"priority must be one of: {', '.join(VALID_PRIORITIES)}")
        return v.lower() if v else None


class TaskResponse(TaskBase):
    """Task response schema."""

    id: UUID
    contact_id: UUID
    category: str | None = None
    subcategory: str | None = None
    assigned_to: str | None = None
    hubspot_task_id: str | None = None
    sync_status: str
    sync_error: str | None = None
    synced_at: datetime | None = None
    ms_teams_message_id: str | None = None
    notification_sent_at: datetime | None = None
    triggered_by_reply_id: UUID | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """Paginated task list response."""

    items: list[TaskResponse]
    total: int
    page: int
    page_size: int
    pages: int


class TaskWithContactResponse(TaskResponse):
    """Task response with contact details."""

    contact_email: str
    contact_name: str
    contact_company: str


# === Email Reply Schemas ===

class EmailReplyResponse(BaseModel):
    """Email reply response schema."""

    id: UUID
    contact_id: UUID
    source: str
    external_id: str
    subject: str | None = None
    body_text: str
    body_html: str | None = None
    received_at: datetime
    main_category: str | None = None
    subcategory: str | None = None
    categorization_confidence: Decimal | None = None
    categorization_reasoning: str | None = None
    categorized_at: datetime | None = None
    processed: bool
    tasks_created: bool = False
    notification_sent: bool = False
    processing_error: str | None = None
    campaign_external_id: str | None = None
    thread_id: str | None = None
    in_reply_to: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class EmailReplyListResponse(BaseModel):
    """Paginated email reply list response."""

    items: list[EmailReplyResponse]
    total: int
    page: int
    page_size: int
    pages: int


# === Dashboard Schemas ===

class CategoryCount(BaseModel):
    """Count by category."""

    category: str
    count: int


class PriorityCount(BaseModel):
    """Count by priority."""

    priority: str
    count: int


class DashboardStats(BaseModel):
    """Dashboard statistics."""

    total_contacts: int
    total_tasks: int
    total_replies: int
    pending_tasks: int
    synced_tasks: int
    failed_tasks: int
    contacts_by_category: list[CategoryCount]
    tasks_by_priority: list[PriorityCount]
    replies_today: int
    tasks_due_today: int


class RecentActivity(BaseModel):
    """Recent activity item."""

    type: str  # "reply", "task", "contact"
    id: UUID
    title: str
    description: str
    timestamp: datetime
    priority: str | None = None
    category: str | None = None


class RecentActivityResponse(BaseModel):
    """Recent activity list."""

    items: list[RecentActivity]


# === Common Schemas ===

class MessageResponse(BaseModel):
    """Simple message response."""

    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    detail: str | None = None

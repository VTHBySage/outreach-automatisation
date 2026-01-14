"""Contact management API endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.api.v1.schemas import (
    ContactCreate,
    ContactListResponse,
    ContactResponse,
    ContactUpdate,
    EmailReplyListResponse,
    EmailReplyResponse,
    MessageResponse,
    TaskListResponse,
    TaskResponse,
)
from app.core.logging import get_logger
from app.db.models.contact import Contact
from app.db.models.email_reply import EmailReply
from app.db.models.task import Task
from app.dependencies import DbSession

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=ContactListResponse)
async def list_contacts(
    session: DbSession,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: str | None = Query(None, description="Search by email, name, or company"),
    category: str | None = Query(None, description="Filter by category"),
    validation_status: str | None = Query(None, description="Filter by validation status"),
):
    """List contacts with pagination and filters."""
    # Build query
    query = select(Contact).where(Contact.deleted_at.is_(None))

    # Apply filters
    if search:
        search_term = f"%{search}%"
        query = query.where(
            (Contact.email.ilike(search_term))
            | (Contact.first_name.ilike(search_term))
            | (Contact.last_name.ilike(search_term))
            | (Contact.company_name.ilike(search_term))
        )

    if category:
        query = query.where(Contact.current_category == category)

    if validation_status:
        query = query.where(Contact.validation_status == validation_status)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.order_by(Contact.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    # Execute
    result = await session.execute(query)
    contacts = result.scalars().all()

    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return ContactListResponse(
        items=[ContactResponse.model_validate(c) for c in contacts],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    session: DbSession,
    contact_id: UUID,
):
    """Get a single contact by ID."""
    contact = await session.get(Contact, contact_id)

    if not contact or contact.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Contact not found")

    return ContactResponse.model_validate(contact)


@router.post("", response_model=ContactResponse, status_code=201)
async def create_contact(
    session: DbSession,
    data: ContactCreate,
):
    """Create a new contact."""
    # Check for existing contact with same email
    existing = await session.execute(
        select(Contact).where(Contact.email == data.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Contact with this email already exists")

    contact = Contact(**data.model_dump())
    session.add(contact)
    await session.flush()
    await session.refresh(contact)

    logger.info("contact_created", contact_id=str(contact.id), email=contact.email)

    return ContactResponse.model_validate(contact)


@router.patch("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    session: DbSession,
    contact_id: UUID,
    data: ContactUpdate,
):
    """Update a contact."""
    contact = await session.get(Contact, contact_id)

    if not contact or contact.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Contact not found")

    # Update only provided fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contact, field, value)

    await session.flush()
    await session.refresh(contact)

    logger.info("contact_updated", contact_id=str(contact.id))

    return ContactResponse.model_validate(contact)


@router.delete("/{contact_id}", response_model=MessageResponse)
async def delete_contact(
    session: DbSession,
    contact_id: UUID,
):
    """Soft delete a contact."""
    from datetime import datetime

    contact = await session.get(Contact, contact_id)

    if not contact or contact.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Contact not found")

    contact.deleted_at = datetime.utcnow()
    await session.flush()

    logger.info("contact_deleted", contact_id=str(contact.id))

    return MessageResponse(message="Contact deleted successfully")


@router.get("/{contact_id}/tasks", response_model=TaskListResponse)
async def get_contact_tasks(
    session: DbSession,
    contact_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, description="Filter by sync status"),
):
    """Get tasks for a specific contact."""
    # Verify contact exists
    contact = await session.get(Contact, contact_id)
    if not contact or contact.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Contact not found")

    # Build query
    query = select(Task).where(Task.contact_id == contact_id)

    if status:
        query = query.where(Task.sync_status == status)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.order_by(Task.due_date.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    tasks = result.scalars().all()

    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return TaskListResponse(
        items=[TaskResponse.model_validate(t) for t in tasks],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{contact_id}/replies", response_model=EmailReplyListResponse)
async def get_contact_replies(
    session: DbSession,
    contact_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Get email replies for a specific contact."""
    # Verify contact exists
    contact = await session.get(Contact, contact_id)
    if not contact or contact.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Contact not found")

    # Build query
    query = select(EmailReply).where(EmailReply.contact_id == contact_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.order_by(EmailReply.received_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    replies = result.scalars().all()

    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return EmailReplyListResponse(
        items=[EmailReplyResponse.model_validate(r) for r in replies],
        total=total,
        page=page,
        page_size=page_size,
    )

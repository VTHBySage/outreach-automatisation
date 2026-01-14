"""Task management API endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.api.v1.schemas import (
    MessageResponse,
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
    TaskWithContactResponse,
)
from app.core.constants import TaskPriority, TaskStatus
from app.core.logging import get_logger
from app.db.models.contact import Contact
from app.db.models.task import Task
from app.dependencies import DbSession

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    session: DbSession,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    priority: str | None = Query(None, description="Filter by priority"),
    sync_status: str | None = Query(None, description="Filter by sync status"),
    assigned_to: str | None = Query(None, description="Filter by assignee"),
    due_before: datetime | None = Query(None, description="Filter by due date (before)"),
    due_after: datetime | None = Query(None, description="Filter by due date (after)"),
    completed: bool | None = Query(None, description="Filter by completion status"),
):
    """List tasks with pagination and filters."""
    # Build query
    query = select(Task)

    # Apply filters
    if priority:
        query = query.where(Task.priority == priority)

    if sync_status:
        query = query.where(Task.sync_status == sync_status)

    if assigned_to:
        query = query.where(Task.assigned_to == assigned_to)

    if due_before:
        query = query.where(Task.due_date <= due_before)

    if due_after:
        query = query.where(Task.due_date >= due_after)

    if completed is not None:
        if completed:
            query = query.where(Task.completed_at.isnot(None))
        else:
            query = query.where(Task.completed_at.is_(None))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and ordering
    query = query.order_by(Task.due_date.asc(), Task.priority.desc())
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


@router.get("/pending", response_model=list[TaskWithContactResponse])
async def list_pending_tasks(
    session: DbSession,
    limit: int = Query(50, ge=1, le=200, description="Max tasks to return"),
):
    """Get pending tasks with contact details, ordered by priority and due date."""
    query = (
        select(Task, Contact)
        .join(Contact, Task.contact_id == Contact.id)
        .where(Task.completed_at.is_(None))
        .where(Contact.deleted_at.is_(None))
        .order_by(
            # Priority order: highest > high > medium > low
            func.case(
                (Task.priority == TaskPriority.HIGHEST.value, 1),
                (Task.priority == TaskPriority.HIGH.value, 2),
                (Task.priority == TaskPriority.MEDIUM.value, 3),
                (Task.priority == TaskPriority.LOW.value, 4),
                else_=5,
            ),
            Task.due_date.asc(),
        )
        .limit(limit)
    )

    result = await session.execute(query)
    rows = result.all()

    return [
        TaskWithContactResponse(
            **TaskResponse.model_validate(task).model_dump(),
            contact_email=contact.email,
            contact_name=contact.full_name,
            contact_company=contact.company_name,
        )
        for task, contact in rows
    ]


@router.get("/due-today", response_model=list[TaskWithContactResponse])
async def list_tasks_due_today(
    session: DbSession,
):
    """Get tasks due today with contact details."""
    from datetime import date

    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())

    query = (
        select(Task, Contact)
        .join(Contact, Task.contact_id == Contact.id)
        .where(Task.due_date >= today_start)
        .where(Task.due_date <= today_end)
        .where(Task.completed_at.is_(None))
        .where(Contact.deleted_at.is_(None))
        .order_by(Task.priority.desc(), Task.due_date.asc())
    )

    result = await session.execute(query)
    rows = result.all()

    return [
        TaskWithContactResponse(
            **TaskResponse.model_validate(task).model_dump(),
            contact_email=contact.email,
            contact_name=contact.full_name,
            contact_company=contact.company_name,
        )
        for task, contact in rows
    ]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    session: DbSession,
    task_id: UUID,
):
    """Get a single task by ID."""
    task = await session.get(Task, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskResponse.model_validate(task)


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    session: DbSession,
    data: TaskCreate,
):
    """Create a new task."""
    # Verify contact exists
    contact = await session.get(Contact, data.contact_id)
    if not contact or contact.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Contact not found")

    task = Task(
        **data.model_dump(),
        sync_status=TaskStatus.PENDING.value,
    )
    session.add(task)
    await session.flush()
    await session.refresh(task)

    logger.info(
        "task_created",
        task_id=str(task.id),
        contact_id=str(data.contact_id),
        priority=task.priority,
    )

    return TaskResponse.model_validate(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    session: DbSession,
    task_id: UUID,
    data: TaskUpdate,
):
    """Update a task."""
    task = await session.get(Task, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Update only provided fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    await session.flush()
    await session.refresh(task)

    logger.info("task_updated", task_id=str(task.id))

    return TaskResponse.model_validate(task)


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    session: DbSession,
    task_id: UUID,
):
    """Mark a task as completed."""
    task = await session.get(Task, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.completed_at:
        raise HTTPException(status_code=400, detail="Task is already completed")

    task.completed_at = datetime.utcnow()
    await session.flush()
    await session.refresh(task)

    logger.info("task_completed", task_id=str(task.id))

    return TaskResponse.model_validate(task)


@router.post("/{task_id}/reopen", response_model=TaskResponse)
async def reopen_task(
    session: DbSession,
    task_id: UUID,
):
    """Reopen a completed task."""
    task = await session.get(Task, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not task.completed_at:
        raise HTTPException(status_code=400, detail="Task is not completed")

    task.completed_at = None
    await session.flush()
    await session.refresh(task)

    logger.info("task_reopened", task_id=str(task.id))

    return TaskResponse.model_validate(task)


@router.post("/{task_id}/sync", response_model=MessageResponse)
async def trigger_task_sync(
    session: DbSession,
    task_id: UUID,
):
    """Trigger HubSpot sync for a task."""
    from app.workers.hubspot_tasks import create_hubspot_task

    task = await session.get(Task, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Queue sync task
    create_hubspot_task.delay(task_id=str(task.id))

    logger.info("task_sync_triggered", task_id=str(task.id))

    return MessageResponse(message="Task sync queued")


@router.delete("/{task_id}", response_model=MessageResponse)
async def delete_task(
    session: DbSession,
    task_id: UUID,
):
    """Delete a task."""
    task = await session.get(Task, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await session.delete(task)
    await session.flush()

    logger.info("task_deleted", task_id=str(task_id))

    return MessageResponse(message="Task deleted successfully")

"""Dashboard API endpoints for metrics and recent activity."""

from datetime import date, datetime

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.v1.schemas import (
    CategoryCount,
    DashboardStats,
    PriorityCount,
    RecentActivity,
    RecentActivityResponse,
)
from app.core.constants import TaskStatus
from app.core.logging import get_logger
from app.db.models.contact import Contact
from app.db.models.email_reply import EmailReply
from app.db.models.task import Task
from app.dependencies import DbSession

logger = get_logger(__name__)
router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    session: DbSession,
):
    """Get dashboard statistics."""
    # Total contacts (not deleted)
    contacts_result = await session.execute(
        select(func.count()).select_from(Contact).where(Contact.deleted_at.is_(None))
    )
    total_contacts = contacts_result.scalar() or 0

    # Total tasks
    tasks_result = await session.execute(select(func.count()).select_from(Task))
    total_tasks = tasks_result.scalar() or 0

    # Total replies
    replies_result = await session.execute(select(func.count()).select_from(EmailReply))
    total_replies = replies_result.scalar() or 0

    # Tasks by sync status
    pending_result = await session.execute(
        select(func.count())
        .select_from(Task)
        .where(Task.sync_status == TaskStatus.PENDING.value)
    )
    pending_tasks = pending_result.scalar() or 0

    synced_result = await session.execute(
        select(func.count())
        .select_from(Task)
        .where(Task.sync_status == TaskStatus.SYNCED.value)
    )
    synced_tasks = synced_result.scalar() or 0

    failed_result = await session.execute(
        select(func.count())
        .select_from(Task)
        .where(Task.sync_status == TaskStatus.FAILED.value)
    )
    failed_tasks = failed_result.scalar() or 0

    # Contacts by category
    category_query = (
        select(Contact.current_category, func.count())
        .where(Contact.deleted_at.is_(None))
        .where(Contact.current_category.isnot(None))
        .group_by(Contact.current_category)
    )
    category_result = await session.execute(category_query)
    contacts_by_category = [
        CategoryCount(category=row[0], count=row[1]) for row in category_result.all()
    ]

    # Tasks by priority
    priority_query = select(Task.priority, func.count()).group_by(Task.priority)
    priority_result = await session.execute(priority_query)
    tasks_by_priority = [
        PriorityCount(priority=row[0], count=row[1]) for row in priority_result.all()
    ]

    # Replies today
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())

    replies_today_result = await session.execute(
        select(func.count())
        .select_from(EmailReply)
        .where(EmailReply.received_at >= today_start)
        .where(EmailReply.received_at <= today_end)
    )
    replies_today = replies_today_result.scalar() or 0

    # Tasks due today
    tasks_due_today_result = await session.execute(
        select(func.count())
        .select_from(Task)
        .where(Task.due_date >= today_start)
        .where(Task.due_date <= today_end)
        .where(Task.completed_at.is_(None))
    )
    tasks_due_today = tasks_due_today_result.scalar() or 0

    return DashboardStats(
        total_contacts=total_contacts,
        total_tasks=total_tasks,
        total_replies=total_replies,
        pending_tasks=pending_tasks,
        synced_tasks=synced_tasks,
        failed_tasks=failed_tasks,
        contacts_by_category=contacts_by_category,
        tasks_by_priority=tasks_by_priority,
        replies_today=replies_today,
        tasks_due_today=tasks_due_today,
    )


@router.get("/recent", response_model=RecentActivityResponse)
async def get_recent_activity(
    session: DbSession,
    limit: int = Query(20, ge=1, le=100, description="Max items to return"),
):
    """Get recent activity (contacts, tasks, replies)."""
    activities: list[RecentActivity] = []

    # Recent contacts
    contacts_query = (
        select(Contact)
        .where(Contact.deleted_at.is_(None))
        .order_by(Contact.created_at.desc())
        .limit(limit // 3)
    )
    contacts_result = await session.execute(contacts_query)
    for contact in contacts_result.scalars().all():
        activities.append(
            RecentActivity(
                type="contact",
                id=contact.id,
                title=f"New contact: {contact.full_name}",
                description=f"{contact.email} from {contact.company_name}",
                timestamp=contact.created_at,
                category=contact.current_category,
            )
        )

    # Recent tasks
    tasks_query = (
        select(Task)
        .order_by(Task.created_at.desc())
        .limit(limit // 3)
    )
    tasks_result = await session.execute(tasks_query)
    for task in tasks_result.scalars().all():
        activities.append(
            RecentActivity(
                type="task",
                id=task.id,
                title=task.title,
                description=task.task_type.replace("_", " ").title(),
                timestamp=task.created_at,
                priority=task.priority,
                category=task.category,
            )
        )

    # Recent replies
    replies_query = (
        select(EmailReply)
        .order_by(EmailReply.received_at.desc())
        .limit(limit // 3)
    )
    replies_result = await session.execute(replies_query)
    for reply in replies_result.scalars().all():
        activities.append(
            RecentActivity(
                type="reply",
                id=reply.id,
                title=reply.subject or "Email reply",
                description=reply.body_text[:100] + "..." if len(reply.body_text) > 100 else reply.body_text,
                timestamp=reply.received_at,
                category=reply.main_category,
            )
        )

    # Sort all activities by timestamp
    activities.sort(key=lambda x: x.timestamp, reverse=True)

    return RecentActivityResponse(items=activities[:limit])


@router.get("/sync-status")
async def get_sync_status(
    session: DbSession,
):
    """Get HubSpot sync status overview."""
    # Tasks sync status
    task_status_query = (
        select(Task.sync_status, func.count())
        .group_by(Task.sync_status)
    )
    task_result = await session.execute(task_status_query)
    task_status = {row[0]: row[1] for row in task_result.all()}

    # Contacts with HubSpot ID
    contacts_synced_result = await session.execute(
        select(func.count())
        .select_from(Contact)
        .where(Contact.hubspot_contact_id.isnot(None))
        .where(Contact.deleted_at.is_(None))
    )
    contacts_synced = contacts_synced_result.scalar() or 0

    contacts_unsynced_result = await session.execute(
        select(func.count())
        .select_from(Contact)
        .where(Contact.hubspot_contact_id.is_(None))
        .where(Contact.deleted_at.is_(None))
    )
    contacts_unsynced = contacts_unsynced_result.scalar() or 0

    # Failed tasks with errors
    failed_tasks_query = (
        select(Task.id, Task.title, Task.sync_error)
        .where(Task.sync_status == TaskStatus.FAILED.value)
        .order_by(Task.updated_at.desc())
        .limit(10)
    )
    failed_result = await session.execute(failed_tasks_query)
    failed_tasks = [
        {
            "id": str(row[0]),
            "title": row[1],
            "error": row[2],
        }
        for row in failed_result.all()
    ]

    return {
        "tasks": {
            "pending": task_status.get(TaskStatus.PENDING.value, 0),
            "synced": task_status.get(TaskStatus.SYNCED.value, 0),
            "failed": task_status.get(TaskStatus.FAILED.value, 0),
        },
        "contacts": {
            "synced": contacts_synced,
            "unsynced": contacts_unsynced,
        },
        "recent_failures": failed_tasks,
    }


@router.get("/re-engagement")
async def get_re_engagement_contacts(
    session: DbSession,
    days_ahead: int = Query(7, ge=1, le=30, description="Days to look ahead"),
):
    """Get contacts due for re-engagement."""
    from datetime import timedelta

    today = date.today()
    end_date = today + timedelta(days=days_ahead)

    query = (
        select(Contact)
        .where(Contact.deleted_at.is_(None))
        .where(Contact.re_engagement_date.isnot(None))
        .where(Contact.re_engagement_date <= datetime.combine(end_date, datetime.max.time()))
        .order_by(Contact.re_engagement_date.asc())
    )

    result = await session.execute(query)
    contacts = result.scalars().all()

    return {
        "total": len(contacts),
        "contacts": [
            {
                "id": str(c.id),
                "email": c.email,
                "name": c.full_name,
                "company": c.company_name,
                "re_engagement_date": c.re_engagement_date.isoformat() if c.re_engagement_date else None,
                "category": c.re_engagement_category,
                "last_category": c.current_category,
            }
            for c in contacts
        ],
    }

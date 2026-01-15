"""Dashboard API endpoints for metrics and recent activity."""

from datetime import date, datetime

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.v1.schemas import (
    CampaignROI,
    CategoryCount,
    DashboardStats,
    EmailEngagementStats,
    EmailMetricsDashboard,
    PriorityCount,
    RecentActivity,
    RecentActivityResponse,
    ROIDashboard,
)
from app.core.constants import TaskStatus
from app.core.logging import get_logger
from app.db.models.campaign import Campaign
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


@router.get("/email-metrics", response_model=EmailMetricsDashboard)
async def get_email_metrics(
    session: DbSession,
):
    """
    Get email engagement metrics dashboard.

    Returns metrics from Prometheus counters plus database queries
    for conversion funnel tracking.
    """
    from prometheus_client import REGISTRY

    from app.core.constants import MainCategory

    def get_metric_value(metric_name: str, labels: dict | None = None) -> int:
        """Get current value of a Prometheus counter."""
        try:
            for metric in REGISTRY.collect():
                if metric.name == metric_name:
                    for sample in metric.samples:
                        if sample.name == f"{metric_name}_total":
                            if labels is None:
                                # Sum all labels
                                return int(sample.value)
                            elif all(sample.labels.get(k) == v for k, v in labels.items()):
                                return int(sample.value)
            return 0
        except Exception:
            return 0

    def sum_metric(metric_name: str) -> int:
        """Sum all label combinations of a metric."""
        total = 0
        try:
            for metric in REGISTRY.collect():
                if metric.name == metric_name:
                    for sample in metric.samples:
                        if sample.name == f"{metric_name}_total":
                            total += int(sample.value)
        except Exception:
            pass
        return total

    # Get totals from Prometheus
    total_opens = sum_metric("email_opens")
    total_clicks = sum_metric("email_clicks")
    total_replies = sum_metric("email_replies")
    total_bounces = sum_metric("email_bounces")
    total_unsubscribes = sum_metric("email_unsubscribes")

    # Calculate rates (using replies as baseline for sent approximation)
    # In production, you'd track emails_sent metric separately
    total_sent = await session.execute(
        select(func.count()).select_from(EmailReply).where(EmailReply.processed == True)
    )
    sent_count = total_sent.scalar() or 1  # Avoid division by zero

    # Calculate conversion funnel from database
    # Leads -> Replies -> Interested -> Meetings
    interested_result = await session.execute(
        select(func.count())
        .select_from(Contact)
        .where(Contact.current_category == MainCategory.INTERESTED.value)
        .where(Contact.deleted_at.is_(None))
    )
    interested_count = interested_result.scalar() or 0

    # Tasks of type "follow_up_meeting" or similar indicate meetings
    meeting_tasks_result = await session.execute(
        select(func.count())
        .select_from(Task)
        .where(Task.task_type.ilike("%meeting%"))
    )
    meetings_booked = meeting_tasks_result.scalar() or 0

    # Today's metrics from database (since Prometheus resets on restart)
    today_start = datetime.combine(date.today(), datetime.min.time())

    today_replies_result = await session.execute(
        select(func.count())
        .select_from(EmailReply)
        .where(EmailReply.received_at >= today_start)
    )
    today_replies = today_replies_result.scalar() or 0

    total_engagement = EmailEngagementStats(
        opens=total_opens,
        clicks=total_clicks,
        replies=total_replies,
        bounces=total_bounces,
        unsubscribes=total_unsubscribes,
        open_rate=round(total_opens / sent_count * 100, 2) if sent_count > 0 else None,
        click_rate=round(total_clicks / sent_count * 100, 2) if sent_count > 0 else None,
        reply_rate=round(total_replies / sent_count * 100, 2) if sent_count > 0 else None,
        bounce_rate=round(total_bounces / sent_count * 100, 2) if sent_count > 0 else None,
    )

    today_engagement = EmailEngagementStats(
        opens=0,  # Would need timestamp tracking in Prometheus
        clicks=0,
        replies=today_replies,
        bounces=0,
        unsubscribes=0,
    )

    # Conversion funnel
    total_contacts_result = await session.execute(
        select(func.count())
        .select_from(Contact)
        .where(Contact.deleted_at.is_(None))
    )
    total_contacts = total_contacts_result.scalar() or 0

    total_replied_result = await session.execute(
        select(func.count(Contact.id.distinct()))
        .select_from(Contact)
        .join(EmailReply, Contact.id == EmailReply.contact_id)
        .where(Contact.deleted_at.is_(None))
    )
    total_replied = total_replied_result.scalar() or 0

    conversion_funnel = {
        "contacts": total_contacts,
        "replied": total_replied,
        "interested": interested_count,
        "meetings_booked": meetings_booked,
    }

    return EmailMetricsDashboard(
        total_engagement=total_engagement,
        today_engagement=today_engagement,
        conversion_funnel=conversion_funnel,
        top_campaigns=None,  # Use /roi endpoint for campaign-level tracking
    )


@router.get("/roi", response_model=ROIDashboard)
async def get_campaign_roi(
    session: DbSession,
):
    """
    Get Campaign ROI Dashboard.

    Calculates comprehensive ROI metrics including:
    - Cost per lead and cost per meeting
    - Conversion rates at each funnel stage
    - Potential revenue based on meetings booked
    - Overall ROI percentage
    """
    from decimal import Decimal

    from app.core.constants import MainCategory

    # Get all active campaigns with their metrics
    campaigns_query = select(Campaign).where(
        Campaign.deleted_at.is_(None),
        Campaign.status == "active",
    )
    campaigns_result = await session.execute(campaigns_query)
    campaigns = campaigns_result.scalars().all()

    campaign_rois: list[CampaignROI] = []
    total_emails_sent = 0
    total_cost = Decimal("0")
    total_replies = 0
    total_interested = 0
    total_meetings = 0
    total_potential_revenue = Decimal("0")

    for campaign in campaigns:
        # Get contacts in this campaign
        contacts_in_campaign = await session.execute(
            select(func.count())
            .select_from(Contact)
            .where(Contact.campaign_id == campaign.id)
            .where(Contact.deleted_at.is_(None))
        )
        contacts_count = contacts_in_campaign.scalar() or 0

        # Get replies for contacts in this campaign
        replies_query = await session.execute(
            select(func.count())
            .select_from(EmailReply)
            .join(Contact, EmailReply.contact_id == Contact.id)
            .where(Contact.campaign_id == campaign.id)
            .where(Contact.deleted_at.is_(None))
        )
        replies_count = replies_query.scalar() or 0

        # Get interested leads in this campaign
        interested_query = await session.execute(
            select(func.count())
            .select_from(Contact)
            .where(Contact.campaign_id == campaign.id)
            .where(Contact.current_category == MainCategory.INTERESTED.value)
            .where(Contact.deleted_at.is_(None))
        )
        interested_count = interested_query.scalar() or 0

        # Get meetings booked for this campaign
        meetings_query = await session.execute(
            select(func.count())
            .select_from(Task)
            .join(Contact, Task.contact_id == Contact.id)
            .where(Contact.campaign_id == campaign.id)
            .where(Task.task_type.ilike("%meeting%"))
        )
        meetings_count = meetings_query.scalar() or 0

        # Calculate campaign metrics
        emails_sent = campaign.total_emails_sent or contacts_count
        cost_per_email = float(campaign.cost_per_email or Decimal("0.05"))
        campaign_cost = emails_sent * cost_per_email
        avg_deal_value = float(campaign.average_deal_value or Decimal("5000.00"))

        # Calculate rates
        conversion_rate = (replies_count / emails_sent * 100) if emails_sent > 0 else 0.0
        meeting_rate = (meetings_count / replies_count * 100) if replies_count > 0 else 0.0

        # Calculate cost metrics
        cost_per_lead = campaign_cost / replies_count if replies_count > 0 else None
        cost_per_meeting = campaign_cost / meetings_count if meetings_count > 0 else None

        # Calculate potential revenue and ROI
        potential_revenue = meetings_count * avg_deal_value
        roi_percentage = None
        if campaign_cost > 0:
            roi_percentage = ((potential_revenue - campaign_cost) / campaign_cost) * 100

        campaign_roi = CampaignROI(
            campaign_id=str(campaign.id),
            campaign_name=campaign.name,
            emails_sent=emails_sent,
            opens=0,  # Would need SmartLead tracking data
            clicks=0,  # Would need SmartLead tracking data
            replies=replies_count,
            interested_leads=interested_count,
            meetings_booked=meetings_count,
            conversion_rate=round(conversion_rate, 2),
            meeting_rate=round(meeting_rate, 2),
            cost_per_email=cost_per_email,
            total_cost=round(campaign_cost, 2),
            cost_per_lead=round(cost_per_lead, 2) if cost_per_lead else None,
            cost_per_meeting=round(cost_per_meeting, 2) if cost_per_meeting else None,
            average_deal_value=avg_deal_value,
            potential_revenue=round(potential_revenue, 2),
            roi_percentage=round(roi_percentage, 2) if roi_percentage else None,
        )
        campaign_rois.append(campaign_roi)

        # Accumulate totals
        total_emails_sent += emails_sent
        total_cost += Decimal(str(campaign_cost))
        total_replies += replies_count
        total_interested += interested_count
        total_meetings += meetings_count
        total_potential_revenue += Decimal(str(potential_revenue))

    # Calculate overall metrics
    overall_reply_rate = (total_replies / total_emails_sent * 100) if total_emails_sent > 0 else 0.0
    overall_meeting_rate = (total_meetings / total_replies * 100) if total_replies > 0 else 0.0
    overall_cost_per_lead = float(total_cost / total_replies) if total_replies > 0 else None
    overall_cost_per_meeting = float(total_cost / total_meetings) if total_meetings > 0 else None
    overall_roi = None
    if total_cost > 0:
        overall_roi = float((total_potential_revenue - total_cost) / total_cost * 100)

    return ROIDashboard(
        total_emails_sent=total_emails_sent,
        total_cost=round(float(total_cost), 2),
        total_replies=total_replies,
        total_interested=total_interested,
        total_meetings=total_meetings,
        overall_reply_rate=round(overall_reply_rate, 2),
        overall_meeting_rate=round(overall_meeting_rate, 2),
        overall_cost_per_lead=round(overall_cost_per_lead, 2) if overall_cost_per_lead else None,
        overall_cost_per_meeting=round(overall_cost_per_meeting, 2) if overall_cost_per_meeting else None,
        potential_revenue=round(float(total_potential_revenue), 2),
        overall_roi_percentage=round(overall_roi, 2) if overall_roi else None,
        campaigns=campaign_rois,
    )

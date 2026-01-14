"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from app.config import settings

# Create Celery app
celery_app = Celery(
    "outreach_automation",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Reliability
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Limits
    task_time_limit=300,  # 5 minutes max
    task_soft_time_limit=240,  # 4 minutes soft limit
    # Retry
    task_default_retry_delay=60,
    task_max_retries=3,
    # Task routes - separate queues for isolation
    task_routes={
        "app.workers.webhook_tasks.*": {"queue": "webhooks"},
        "app.workers.categorization_tasks.*": {"queue": "categorization"},
        "app.workers.hubspot_tasks.*": {"queue": "hubspot"},
        "app.workers.notification_tasks.*": {"queue": "notifications"},
        "app.workers.scheduler_tasks.*": {"queue": "scheduler"},
        "app.workers.linkedin_tasks.*": {"queue": "linkedin"},
    },
    # Default queue
    task_default_queue="default",
    # Worker prefetch
    worker_prefetch_multiplier=4,
    # Result expiration
    result_expires=3600,  # 1 hour
)

# Auto-discover tasks
celery_app.autodiscover_tasks(
    [
        "app.workers.webhook_tasks",
        "app.workers.categorization_tasks",
        "app.workers.hubspot_tasks",
        "app.workers.notification_tasks",
        "app.workers.scheduler_tasks",
        "app.workers.linkedin_tasks",
    ]
)


# Beat schedule for periodic tasks using crontab for predictable timing
celery_app.conf.beat_schedule = {
    "daily-reengagement-scan": {
        "task": "app.workers.scheduler_tasks.process_reengagement_contacts",
        "schedule": crontab(hour=9, minute=0),  # 9 AM daily
    },
    "weekly-webhook-log-cleanup": {
        "task": "app.workers.scheduler_tasks.cleanup_stale_webhook_logs",
        "schedule": crontab(hour=3, minute=0, day_of_week="sunday"),  # 3 AM Sundays
        "args": (30,),  # Delete logs older than 30 days
    },
    "hourly-pending-tasks-sync": {
        "task": "app.workers.scheduler_tasks.sync_all_pending_tasks",
        "schedule": crontab(minute=0),  # Every hour on the hour
    },
    "linkedin-message-processor": {
        "task": "app.workers.linkedin_tasks.process_approved_linkedin_messages",
        "schedule": crontab(minute="*/10"),  # Every 10 minutes
    },
    "linkedin-approval-checker": {
        "task": "app.workers.linkedin_tasks.check_task_completion_for_approval",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
    },
}

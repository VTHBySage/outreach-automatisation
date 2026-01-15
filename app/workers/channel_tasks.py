"""Celery tasks for channel switching automation.

Handles automatic channel escalation:
- Email → LinkedIn (after 3 days no response)
- LinkedIn → Phone (after 5 more days no response)
"""

import asyncio

from celery import shared_task

from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.services.channel_switching.service import ChannelSwitchingService

logger = get_logger(__name__)


@shared_task(
    name="app.workers.channel_tasks.process_channel_switches",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def process_channel_switches(self) -> dict[str, int]:
    """
    Daily task to check and process channel switches for all contacts.

    This task:
    1. Finds contacts that haven't responded on their current channel
    2. Switches Email → LinkedIn after EMAIL_TO_LINKEDIN_DAYS
    3. Switches LinkedIn → Phone after LINKEDIN_TO_PHONE_DAYS

    Scheduled to run daily at 10 AM via Celery beat.

    Returns:
        Dict with counts: {'to_linkedin': N, 'to_phone': M, 'skipped': S, 'errors': E}
    """
    try:
        return asyncio.get_event_loop().run_until_complete(
            _process_channel_switches_async()
        )
    except RuntimeError:
        # No event loop running, create a new one
        return asyncio.run(_process_channel_switches_async())
    except Exception as e:
        logger.error("channel_switching_task_failed", error=str(e))
        raise self.retry(exc=e)


async def _process_channel_switches_async() -> dict[str, int]:
    """Async implementation of channel switch processing."""
    async with async_session_factory() as session:
        service = ChannelSwitchingService(session)
        results = await service.process_all_channel_switches()

        logger.info(
            "channel_switching_complete",
            to_linkedin=results["to_linkedin"],
            to_phone=results["to_phone"],
            skipped=results["skipped"],
            errors=results["errors"],
        )

        return results


@shared_task(
    name="app.workers.channel_tasks.switch_contact_channel",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def switch_contact_channel(self, contact_id: str) -> str | None:
    """
    Check and switch channel for a specific contact.

    Can be called manually or triggered by other tasks.

    Args:
        contact_id: UUID string of the contact

    Returns:
        New channel name if switched, None otherwise
    """
    from uuid import UUID

    try:
        return asyncio.get_event_loop().run_until_complete(
            _switch_contact_channel_async(UUID(contact_id))
        )
    except RuntimeError:
        return asyncio.run(_switch_contact_channel_async(UUID(contact_id)))
    except Exception as e:
        logger.error(
            "switch_contact_channel_failed",
            contact_id=contact_id,
            error=str(e),
        )
        raise self.retry(exc=e)


async def _switch_contact_channel_async(contact_id) -> str | None:
    """Async implementation of single contact channel switch."""
    from uuid import UUID

    async with async_session_factory() as session:
        service = ChannelSwitchingService(session)
        new_channel = await service.check_and_switch_channel(contact_id)
        await session.commit()
        return new_channel

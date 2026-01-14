"""Re-engagement scheduling service."""

from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    RE_ENGAGEMENT_DAYS,
    RE_ENGAGEMENT_DAYS_WITH_NPS,
    SubCategory,
)
from app.core.logging import get_logger
from app.db.models.contact import Contact
from app.db.repositories.contact import ContactRepository

logger = get_logger(__name__)


class SchedulerService:
    """Service for managing re-engagement schedules."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.contact_repo = ContactRepository(session)

    async def schedule_reengagement(
        self,
        contact: Contact,
        subcategory: SubCategory,
        nps_survey_sent: bool = False,
    ) -> datetime | None:
        """
        Schedule re-engagement for a contact based on categorization.

        Args:
            contact: The contact to schedule
            subcategory: The categorization that triggers re-engagement
            nps_survey_sent: If True and subcategory is NOT_INTERESTED,
                            use 120-day re-engagement instead of 90-day

        Returns:
            The scheduled re-engagement date, or None if no re-engagement
        """
        days = RE_ENGAGEMENT_DAYS.get(subcategory)

        # Special case: NOT_INTERESTED with NPS survey gets 120 days
        if (
            subcategory == SubCategory.NOT_INTERESTED
            and nps_survey_sent
        ):
            days = RE_ENGAGEMENT_DAYS_WITH_NPS
            logger.info(
                "using_extended_nps_reengagement",
                contact_id=str(contact.id),
                days=days,
            )

        if days is None:
            logger.debug(
                "no_reengagement_scheduled",
                contact_id=str(contact.id),
                subcategory=subcategory.value,
                reason="subcategory_has_no_automatic_reengagement",
            )
            return None

        re_engagement_date = datetime.utcnow() + timedelta(days=days)

        contact.re_engagement_date = re_engagement_date
        contact.re_engagement_category = subcategory.value

        await self.session.flush()

        logger.info(
            "reengagement_scheduled",
            contact_id=str(contact.id),
            subcategory=subcategory.value,
            days=days,
            re_engagement_date=re_engagement_date.isoformat(),
            nps_survey_sent=nps_survey_sent,
        )

        return re_engagement_date

    async def get_contacts_due_for_reengagement(
        self,
        limit: int = 100,
    ) -> list[Contact]:
        """
        Get contacts due for re-engagement.

        Returns contacts where re_engagement_date <= now.
        """
        return await self.contact_repo.get_due_for_reengagement(
            before_date=datetime.utcnow(),
            limit=limit,
        )

    async def clear_reengagement(self, contact: Contact) -> None:
        """Clear re-engagement schedule for a contact."""
        contact.re_engagement_date = None
        contact.re_engagement_category = None
        await self.session.flush()

        logger.info(
            "reengagement_cleared",
            contact_id=str(contact.id),
        )

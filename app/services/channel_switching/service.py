"""Channel switching service for multi-channel orchestration.

Orchestrates the flow: Email → LinkedIn → Phone

When a contact doesn't respond on one channel, automatically
switches to the next channel after a configurable number of days.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import TaskPriority, TaskStatus
from app.core.logging import get_logger
from app.db.models.contact import Contact
from app.db.models.task import Task
from app.integrations.connectsafely import ConnectSafelyClient
from app.services.linkedin.service import LinkedInApprovalService

logger = get_logger(__name__)


class ChannelSwitchingService:
    """
    Service for multi-channel outreach orchestration.

    Manages the flow: Email → LinkedIn → Phone
    based on engagement and response patterns.
    """

    # Configuration: days without response before switching channels
    EMAIL_TO_LINKEDIN_DAYS = 3  # Switch to LinkedIn after 3 days
    LINKEDIN_TO_PHONE_DAYS = 5  # Escalate to phone after 5 more days

    # Valid channel values
    CHANNEL_EMAIL = "email"
    CHANNEL_LINKEDIN = "linkedin"
    CHANNEL_PHONE = "phone"

    def __init__(self, session: AsyncSession):
        self.session = session
        self.linkedin_service = LinkedInApprovalService(session)

    async def check_and_switch_channel(
        self,
        contact_id: UUID,
    ) -> str | None:
        """
        Check if a contact needs to switch channels and execute if needed.

        Args:
            contact_id: UUID of the contact to check

        Returns:
            New channel name if switched, None if no switch needed
        """
        stmt = select(Contact).where(
            and_(
                Contact.id == contact_id,
                Contact.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(stmt)
        contact = result.scalar_one_or_none()

        if not contact:
            logger.warning("channel_switch_contact_not_found", contact_id=str(contact_id))
            return None

        # Calculate days since last engagement
        last_engagement = contact.last_engagement_at or contact.last_contacted_at
        if not last_engagement:
            return None

        days_since_engagement = (datetime.now(timezone.utc) - last_engagement).days

        # Determine if switch is needed based on current channel
        new_channel = None

        if contact.current_channel == self.CHANNEL_EMAIL:
            if days_since_engagement >= self.EMAIL_TO_LINKEDIN_DAYS:
                new_channel = await self._switch_to_linkedin(contact)

        elif contact.current_channel == self.CHANNEL_LINKEDIN:
            if days_since_engagement >= self.LINKEDIN_TO_PHONE_DAYS:
                new_channel = await self._switch_to_phone(contact)

        return new_channel

    async def _switch_to_linkedin(self, contact: Contact) -> str | None:
        """
        Switch contact from email to LinkedIn outreach.

        1. Look up LinkedIn profile
        2. Queue connection request
        3. Update contact channel

        Returns:
            'linkedin' if successful, None otherwise
        """
        # Skip if no LinkedIn URL available
        if not contact.linkedin_url:
            # Try to find profile via email
            try:
                connectsafely = ConnectSafelyClient()
                profile = await connectsafely.find_profile_by_email(contact.email)
                if profile:
                    contact.linkedin_url = profile.get("profile_url")
                    await self.session.flush()
            except Exception as e:
                logger.warning(
                    "linkedin_profile_lookup_failed",
                    contact_id=str(contact.id),
                    error=str(e),
                )

        if not contact.linkedin_url:
            logger.info(
                "channel_switch_skipped_no_linkedin",
                contact_id=str(contact.id),
            )
            return None

        # Queue LinkedIn connection request for approval
        try:
            await self.linkedin_service.queue_connection_request(
                contact=contact,
                profile_url=contact.linkedin_url,
                message=None,  # Connection requests can optionally have a note
                context=f"Auto-escalation: No email response after {self.EMAIL_TO_LINKEDIN_DAYS} days",
            )

            # Update contact channel
            contact.current_channel = self.CHANNEL_LINKEDIN
            contact.channel_switched_at = datetime.now(timezone.utc)
            await self.session.flush()

            logger.info(
                "channel_switched_to_linkedin",
                contact_id=str(contact.id),
                email=contact.email,
            )

            return self.CHANNEL_LINKEDIN

        except Exception as e:
            logger.error(
                "channel_switch_to_linkedin_failed",
                contact_id=str(contact.id),
                error=str(e),
            )
            return None

    async def _switch_to_phone(self, contact: Contact) -> str | None:
        """
        Switch contact from LinkedIn to phone outreach.

        Creates a phone call task for manual follow-up.

        Returns:
            'phone' if successful, None otherwise
        """
        # Create phone call task
        task = Task(
            contact_id=contact.id,
            title=f"Phone Call Required: {contact.full_name}",
            description=self._build_phone_task_description(contact),
            priority=TaskPriority.HIGH.value,
            category="phone_outreach",
            task_type="Phone Call",
            due_date=datetime.now(timezone.utc) + timedelta(hours=24),
            sync_status=TaskStatus.PENDING.value,
        )
        self.session.add(task)

        # Update contact channel
        contact.current_channel = self.CHANNEL_PHONE
        contact.channel_switched_at = datetime.now(timezone.utc)
        await self.session.flush()

        logger.info(
            "channel_switched_to_phone",
            contact_id=str(contact.id),
            email=contact.email,
            task_id=str(task.id),
        )

        return self.CHANNEL_PHONE

    async def get_contacts_for_channel_switch(
        self,
        limit: int = 100,
    ) -> list[Contact]:
        """
        Get contacts that may need channel switching.

        Returns contacts that:
        1. Are not on 'phone' channel (terminal state)
        2. Have been contacted but not responded
        3. Have sufficient time elapsed since last engagement

        Args:
            limit: Maximum contacts to return

        Returns:
            List of contacts to check for channel switching
        """
        # Calculate cutoff dates
        email_cutoff = datetime.now(timezone.utc) - timedelta(days=self.EMAIL_TO_LINKEDIN_DAYS)
        linkedin_cutoff = datetime.now(timezone.utc) - timedelta(days=self.LINKEDIN_TO_PHONE_DAYS)

        # Find email contacts ready to switch
        email_stmt = (
            select(Contact)
            .where(
                and_(
                    Contact.deleted_at.is_(None),
                    Contact.current_channel == self.CHANNEL_EMAIL,
                    Contact.last_contacted_at.isnot(None),
                    Contact.last_response_at.is_(None),  # No response
                    Contact.last_contacted_at <= email_cutoff,
                )
            )
            .limit(limit // 2)
        )

        # Find LinkedIn contacts ready to switch
        linkedin_stmt = (
            select(Contact)
            .where(
                and_(
                    Contact.deleted_at.is_(None),
                    Contact.current_channel == self.CHANNEL_LINKEDIN,
                    Contact.channel_switched_at.isnot(None),
                    Contact.last_response_at.is_(None),  # Still no response
                    Contact.channel_switched_at <= linkedin_cutoff,
                )
            )
            .limit(limit // 2)
        )

        email_result = await self.session.execute(email_stmt)
        linkedin_result = await self.session.execute(linkedin_stmt)

        contacts = list(email_result.scalars().all()) + list(linkedin_result.scalars().all())
        return contacts

    async def process_all_channel_switches(self) -> dict[str, int]:
        """
        Process channel switches for all eligible contacts.

        Returns:
            Dict with counts: {'to_linkedin': N, 'to_phone': M, 'errors': E}
        """
        results = {
            "to_linkedin": 0,
            "to_phone": 0,
            "skipped": 0,
            "errors": 0,
        }

        contacts = await self.get_contacts_for_channel_switch()

        for contact in contacts:
            try:
                new_channel = await self.check_and_switch_channel(contact.id)
                if new_channel == self.CHANNEL_LINKEDIN:
                    results["to_linkedin"] += 1
                elif new_channel == self.CHANNEL_PHONE:
                    results["to_phone"] += 1
                else:
                    results["skipped"] += 1
            except Exception as e:
                logger.error(
                    "channel_switch_error",
                    contact_id=str(contact.id),
                    error=str(e),
                )
                results["errors"] += 1

        await self.session.commit()

        logger.info(
            "channel_switching_batch_complete",
            to_linkedin=results["to_linkedin"],
            to_phone=results["to_phone"],
            skipped=results["skipped"],
            errors=results["errors"],
        )

        return results

    def _build_phone_task_description(self, contact: Contact) -> str:
        """Build description for phone call task."""
        lines = [
            "**Phone Call Required - Multi-channel Escalation**",
            "",
            f"**Contact:** {contact.full_name}",
            f"**Company:** {contact.company_name}",
            f"**Email:** {contact.email}",
        ]

        if contact.phone:
            lines.append(f"**Phone:** {contact.phone}")
        else:
            lines.append("**Phone:** Not available - research required")

        if contact.linkedin_url:
            lines.append(f"**LinkedIn:** {contact.linkedin_url}")

        lines.extend([
            "",
            "---",
            "**Background:**",
            f"- Email outreach: No response after {self.EMAIL_TO_LINKEDIN_DAYS}+ days",
            f"- LinkedIn outreach: No response after {self.LINKEDIN_TO_PHONE_DAYS}+ days",
            "",
            "**Action Required:**",
            "Make a phone call to this contact. If no phone number is available,",
            "research and update the contact record before calling.",
        ])

        return "\n".join(lines)

    async def record_engagement(
        self,
        contact_id: UUID,
        engagement_type: str = "response",
    ) -> None:
        """
        Record an engagement event for a contact.

        Call this when a contact responds via any channel.

        Args:
            contact_id: UUID of the contact
            engagement_type: Type of engagement (response, open, click, etc.)
        """
        stmt = select(Contact).where(Contact.id == contact_id)
        result = await self.session.execute(stmt)
        contact = result.scalar_one_or_none()

        if contact:
            contact.last_engagement_at = datetime.now(timezone.utc)
            if engagement_type == "response":
                contact.last_response_at = datetime.now(timezone.utc)
            await self.session.flush()

            logger.debug(
                "engagement_recorded",
                contact_id=str(contact_id),
                engagement_type=engagement_type,
            )

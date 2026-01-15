"""Contact repository."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.contact import Contact
from app.db.repositories.base import BaseRepository


class ContactRepository(BaseRepository[Contact]):
    """Repository for Contact model operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Contact, session)

    async def get_by_email(self, email: str) -> Contact | None:
        """Get contact by email address."""
        stmt = select(Contact).where(
            Contact.email == email,
            Contact.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_hubspot_id(self, hubspot_id: str) -> Contact | None:
        """Get contact by HubSpot contact ID."""
        stmt = select(Contact).where(
            Contact.hubspot_contact_id == hubspot_id,
            Contact.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_linkedin_url(self, linkedin_url: str) -> Contact | None:
        """Get contact by LinkedIn URL."""
        stmt = select(Contact).where(
            Contact.linkedin_url == linkedin_url,
            Contact.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_due_for_reengagement(
        self,
        before_date: datetime,
        limit: int = 100,
    ) -> list[Contact]:
        """Get contacts due for re-engagement."""
        stmt = (
            select(Contact)
            .where(
                Contact.re_engagement_date <= before_date,
                Contact.deleted_at.is_(None),
            )
            .order_by(Contact.re_engagement_date)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_campaign(
        self,
        campaign_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Contact]:
        """Get contacts by campaign ID."""
        stmt = (
            select(Contact)
            .where(
                Contact.campaign_id == campaign_id,
                Contact.deleted_at.is_(None),
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def soft_delete(self, email: str) -> bool:
        """Soft delete contact by email (for GDPR compliance)."""
        contact = await self.get_by_email(email)
        if contact is None:
            return False

        contact.deleted_at = datetime.utcnow()
        await self.session.flush()
        return True

    async def get_or_create_by_email(
        self,
        email: str,
        first_name: str | None = None,
        last_name: str | None = None,
        company_name: str | None = None,
        **kwargs,
    ) -> tuple[Contact, bool]:
        """
        Get existing contact or create new one.

        Returns:
            Tuple of (Contact, created) where created is True if new contact was created.
        """
        existing = await self.get_by_email(email)
        if existing:
            return existing, False

        # Create new contact
        contact = Contact(
            email=email,
            first_name=first_name,
            last_name=last_name,
            company_name=company_name or "Unknown",
            **kwargs,
        )
        self.session.add(contact)
        await self.session.flush()
        await self.session.refresh(contact)
        return contact, True

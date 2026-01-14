"""Email reply repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.email_reply import EmailReply
from app.db.repositories.base import BaseRepository


class EmailReplyRepository(BaseRepository[EmailReply]):
    """Repository for EmailReply model operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(EmailReply, session)

    async def get_by_external_id(
        self,
        source: str,
        external_id: str,
    ) -> EmailReply | None:
        """Get email reply by source and external ID."""
        stmt = select(EmailReply).where(
            EmailReply.source == source,
            EmailReply.external_id == external_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_unprocessed(self, limit: int = 100) -> list[EmailReply]:
        """Get unprocessed email replies."""
        stmt = (
            select(EmailReply)
            .where(EmailReply.processed == False)  # noqa: E712
            .order_by(EmailReply.created_at)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_contact_id(
        self,
        contact_id: UUID,
        limit: int = 100,
    ) -> list[EmailReply]:
        """Get email replies for a contact."""
        stmt = (
            select(EmailReply)
            .where(EmailReply.contact_id == contact_id)
            .order_by(EmailReply.received_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_from_webhook(
        self,
        contact_id: UUID,
        source: str,
        external_id: str,
        body_text: str,
        subject: str | None = None,
        body_html: str | None = None,
        received_at=None,
        **kwargs,
    ) -> EmailReply:
        """Create email reply from webhook data."""
        from datetime import datetime

        reply = EmailReply(
            contact_id=contact_id,
            source=source,
            external_id=external_id,
            body_text=body_text,
            subject=subject,
            body_html=body_html,
            received_at=received_at or datetime.utcnow(),
            processed=False,
            tasks_created=False,
            notification_sent=False,
            **kwargs,
        )
        self.session.add(reply)
        await self.session.flush()
        await self.session.refresh(reply)
        return reply

    async def mark_as_categorized(
        self,
        reply_id: UUID,
        main_category: str,
        subcategory: str,
        confidence: float,
        reasoning: str | None = None,
    ) -> EmailReply | None:
        """Update email reply with categorization results."""
        from datetime import datetime
        from decimal import Decimal

        reply = await self.get_by_id(reply_id)
        if reply is None:
            return None

        reply.main_category = main_category
        reply.subcategory = subcategory
        reply.categorization_confidence = Decimal(str(confidence))
        reply.categorization_reasoning = reasoning
        reply.categorized_at = datetime.utcnow()

        await self.session.flush()
        await self.session.refresh(reply)
        return reply

    async def mark_as_processed(self, reply_id: UUID) -> EmailReply | None:
        """Mark email reply as fully processed."""
        reply = await self.get_by_id(reply_id)
        if reply is None:
            return None

        reply.processed = True
        await self.session.flush()
        await self.session.refresh(reply)
        return reply

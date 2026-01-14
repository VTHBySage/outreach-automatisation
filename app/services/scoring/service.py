"""Lead scoring service based on engagement and attributes."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import MainCategory, SubCategory, SUBCATEGORY_TO_MAIN
from app.core.logging import get_logger
from app.db.models.contact import Contact
from app.db.models.email_reply import EmailReply
from app.db.models.task import Task

logger = get_logger(__name__)


class ScoreGrade(str, Enum):
    """Lead score grades."""
    HOT = "hot"          # 80-100: Ready to buy
    WARM = "warm"        # 60-79: Engaged, needs nurturing
    COOL = "cool"        # 40-59: Some interest
    COLD = "cold"        # 0-39: Low engagement


@dataclass
class ScoringFactors:
    """Factors that contribute to lead score."""
    # Email engagement (max 40 points)
    email_reply_count: int = 0
    positive_replies: int = 0
    interested_replies: int = 0
    last_reply_days_ago: int | None = None

    # LinkedIn engagement (max 20 points)
    has_linkedin_profile: bool = False
    linkedin_connected: bool = False

    # Company fit (max 20 points)
    company_validated: bool = False
    company_validation_confidence: float = 0.0

    # Recency and activity (max 20 points)
    days_since_first_contact: int = 0
    task_completion_rate: float = 0.0
    has_recent_activity: bool = False


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of score components."""
    email_engagement_score: int
    linkedin_engagement_score: int
    company_fit_score: int
    recency_score: int
    total_score: int
    grade: ScoreGrade
    factors: ScoringFactors


class LeadScoringService:
    """Service for calculating and managing lead scores."""

    # Weight configuration
    MAX_EMAIL_SCORE = 40
    MAX_LINKEDIN_SCORE = 20
    MAX_COMPANY_SCORE = 20
    MAX_RECENCY_SCORE = 20

    # Scoring rules
    POINTS_PER_REPLY = 5
    POINTS_PER_POSITIVE_REPLY = 10
    POINTS_FOR_INTERESTED = 15
    POINTS_FOR_LINKEDIN_PROFILE = 5
    POINTS_FOR_LINKEDIN_CONNECTED = 15
    POINTS_FOR_VALIDATED_COMPANY = 10
    POINTS_FOR_RECENT_ACTIVITY = 10
    POINTS_FOR_HIGH_COMPLETION = 10

    # Thresholds
    RECENT_DAYS = 14  # Activity within 14 days is "recent"
    HOT_THRESHOLD = 80
    WARM_THRESHOLD = 60
    COOL_THRESHOLD = 40

    def __init__(self, session: AsyncSession):
        self.session = session

    async def calculate_score(self, contact_id: UUID) -> ScoreBreakdown:
        """
        Calculate lead score for a contact.

        Args:
            contact_id: Contact UUID

        Returns:
            ScoreBreakdown with detailed scoring information
        """
        contact = await self.session.get(Contact, contact_id)
        if not contact:
            raise ValueError(f"Contact {contact_id} not found")

        factors = await self._gather_scoring_factors(contact)
        breakdown = self._calculate_breakdown(factors)

        logger.info(
            "lead_score_calculated",
            contact_id=str(contact_id),
            score=breakdown.total_score,
            grade=breakdown.grade.value,
        )

        return breakdown

    async def _gather_scoring_factors(self, contact: Contact) -> ScoringFactors:
        """Gather all factors for scoring."""
        now = datetime.utcnow()

        # Get email reply stats
        replies_result = await self.session.execute(
            select(EmailReply)
            .where(EmailReply.contact_id == contact.id)
            .order_by(EmailReply.received_at.desc())
        )
        replies = replies_result.scalars().all()

        # Count reply types
        email_reply_count = len(replies)
        positive_replies = 0
        interested_replies = 0
        last_reply_days_ago = None

        for reply in replies:
            if reply.received_at:
                if last_reply_days_ago is None:
                    last_reply_days_ago = (now - reply.received_at).days

            if reply.main_category:
                try:
                    main_cat = MainCategory(reply.main_category)
                    if main_cat == MainCategory.INTERESTED:
                        interested_replies += 1
                        positive_replies += 1
                    elif main_cat == MainCategory.POSITIVE_SIGNALS:
                        positive_replies += 1
                except ValueError:
                    pass

        # Get task stats
        tasks_result = await self.session.execute(
            select(Task).where(Task.contact_id == contact.id)
        )
        tasks = tasks_result.scalars().all()

        completed_tasks = sum(1 for t in tasks if t.completed_at)
        task_completion_rate = completed_tasks / len(tasks) if tasks else 0.0

        # Recent activity
        recent_cutoff = now - timedelta(days=self.RECENT_DAYS)
        has_recent_activity = any(
            r.received_at and r.received_at >= recent_cutoff
            for r in replies
        )

        # Days since first contact
        days_since_first = 0
        if contact.created_at:
            days_since_first = (now - contact.created_at).days

        return ScoringFactors(
            email_reply_count=email_reply_count,
            positive_replies=positive_replies,
            interested_replies=interested_replies,
            last_reply_days_ago=last_reply_days_ago,
            has_linkedin_profile=bool(contact.linkedin_url),
            linkedin_connected=False,  # Would need ConnectSafely API check
            company_validated=contact.validation_status == "validated",
            company_validation_confidence=float(contact.validation_confidence or 0),
            days_since_first_contact=days_since_first,
            task_completion_rate=task_completion_rate,
            has_recent_activity=has_recent_activity,
        )

    def _calculate_breakdown(self, factors: ScoringFactors) -> ScoreBreakdown:
        """Calculate score breakdown from factors."""
        # Email engagement score
        email_score = 0
        email_score += min(factors.email_reply_count * self.POINTS_PER_REPLY, 15)
        email_score += min(factors.positive_replies * self.POINTS_PER_POSITIVE_REPLY, 15)
        email_score += factors.interested_replies * self.POINTS_FOR_INTERESTED
        email_score = min(email_score, self.MAX_EMAIL_SCORE)

        # LinkedIn engagement score
        linkedin_score = 0
        if factors.has_linkedin_profile:
            linkedin_score += self.POINTS_FOR_LINKEDIN_PROFILE
        if factors.linkedin_connected:
            linkedin_score += self.POINTS_FOR_LINKEDIN_CONNECTED
        linkedin_score = min(linkedin_score, self.MAX_LINKEDIN_SCORE)

        # Company fit score
        company_score = 0
        if factors.company_validated:
            company_score += self.POINTS_FOR_VALIDATED_COMPANY
        # Add confidence-based points
        company_score += int(factors.company_validation_confidence * 10)
        company_score = min(company_score, self.MAX_COMPANY_SCORE)

        # Recency score
        recency_score = 0
        if factors.has_recent_activity:
            recency_score += self.POINTS_FOR_RECENT_ACTIVITY
        if factors.task_completion_rate > 0.5:
            recency_score += self.POINTS_FOR_HIGH_COMPLETION
        # Decay for old contacts with no recent activity
        if factors.last_reply_days_ago and factors.last_reply_days_ago < 30:
            recency_score += max(0, 10 - (factors.last_reply_days_ago // 3))
        recency_score = min(recency_score, self.MAX_RECENCY_SCORE)

        # Total
        total_score = email_score + linkedin_score + company_score + recency_score

        # Determine grade
        if total_score >= self.HOT_THRESHOLD:
            grade = ScoreGrade.HOT
        elif total_score >= self.WARM_THRESHOLD:
            grade = ScoreGrade.WARM
        elif total_score >= self.COOL_THRESHOLD:
            grade = ScoreGrade.COOL
        else:
            grade = ScoreGrade.COLD

        return ScoreBreakdown(
            email_engagement_score=email_score,
            linkedin_engagement_score=linkedin_score,
            company_fit_score=company_score,
            recency_score=recency_score,
            total_score=total_score,
            grade=grade,
            factors=factors,
        )

    async def update_contact_score(self, contact_id: UUID) -> int:
        """
        Calculate and update lead score on contact record.

        Args:
            contact_id: Contact UUID

        Returns:
            New lead score
        """
        breakdown = await self.calculate_score(contact_id)

        # Update contact record
        contact = await self.session.get(Contact, contact_id)
        if contact:
            # Note: This assumes lead_score field exists on Contact model
            # If not, you'd need to add it via migration
            if hasattr(contact, "lead_score"):
                contact.lead_score = breakdown.total_score
                await self.session.flush()

        return breakdown.total_score

    async def get_hot_leads(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        Get contacts with HOT lead scores.

        Returns:
            List of hot lead contact data with scores
        """
        # Get all active contacts
        contacts_result = await self.session.execute(
            select(Contact)
            .where(Contact.deleted_at.is_(None))
            .order_by(Contact.updated_at.desc())
            .limit(200)  # Process more to find hot ones
        )
        contacts = contacts_result.scalars().all()

        hot_leads = []
        for contact in contacts:
            try:
                breakdown = await self.calculate_score(contact.id)
                if breakdown.grade == ScoreGrade.HOT:
                    hot_leads.append({
                        "contact_id": str(contact.id),
                        "email": contact.email,
                        "name": contact.full_name,
                        "company": contact.company_name,
                        "score": breakdown.total_score,
                        "grade": breakdown.grade.value,
                        "breakdown": {
                            "email": breakdown.email_engagement_score,
                            "linkedin": breakdown.linkedin_engagement_score,
                            "company_fit": breakdown.company_fit_score,
                            "recency": breakdown.recency_score,
                        },
                    })
                    if len(hot_leads) >= limit:
                        break
            except Exception as e:
                logger.warning(
                    "score_calculation_failed",
                    contact_id=str(contact.id),
                    error=str(e),
                )
                continue

        return hot_leads

    async def get_scoring_summary(self) -> dict[str, Any]:
        """Get summary of lead scores across all contacts."""
        # Get all active contacts
        contacts_result = await self.session.execute(
            select(Contact)
            .where(Contact.deleted_at.is_(None))
            .limit(500)
        )
        contacts = contacts_result.scalars().all()

        grade_counts = {
            ScoreGrade.HOT.value: 0,
            ScoreGrade.WARM.value: 0,
            ScoreGrade.COOL.value: 0,
            ScoreGrade.COLD.value: 0,
        }
        total_score = 0
        scored_count = 0

        for contact in contacts:
            try:
                breakdown = await self.calculate_score(contact.id)
                grade_counts[breakdown.grade.value] += 1
                total_score += breakdown.total_score
                scored_count += 1
            except Exception:
                continue

        avg_score = total_score / scored_count if scored_count > 0 else 0

        return {
            "total_contacts": len(contacts),
            "scored_contacts": scored_count,
            "average_score": round(avg_score, 1),
            "grade_distribution": grade_counts,
        }

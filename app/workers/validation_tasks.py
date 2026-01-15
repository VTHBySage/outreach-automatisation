"""Celery tasks for LLM-powered company validation.

Handles async validation of leads against campaign criteria:
- Single contact validation
- Batch campaign validation
- Manual review task creation
"""

import asyncio
from uuid import UUID

from celery import shared_task

from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.services.validation import CompanyValidationService

logger = get_logger(__name__)


@shared_task(
    name="app.workers.validation_tasks.validate_contact_company",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def validate_contact_company(self, contact_id: str, campaign_id: str) -> dict:
    """
    Validate a single contact's company against campaign criteria.

    Args:
        contact_id: UUID string of the contact
        campaign_id: UUID string of the campaign with targeting criteria

    Returns:
        Dict with validation result: {
            'is_match': bool,
            'confidence': float,
            'company_type': str,
            'needs_review': bool,
            'status': 'validated' | 'rejected' | 'review'
        }
    """
    try:
        return asyncio.get_event_loop().run_until_complete(
            _validate_contact_async(UUID(contact_id), UUID(campaign_id))
        )
    except RuntimeError:
        # No event loop running, create a new one
        return asyncio.run(_validate_contact_async(UUID(contact_id), UUID(campaign_id)))
    except Exception as e:
        logger.error(
            "contact_validation_task_failed",
            contact_id=contact_id,
            campaign_id=campaign_id,
            error=str(e),
        )
        raise self.retry(exc=e)


async def _validate_contact_async(contact_id: UUID, campaign_id: UUID) -> dict:
    """Async implementation of single contact validation."""
    async with async_session_factory() as session:
        service = CompanyValidationService(session)
        result = await service.validate_contact(contact_id, campaign_id)
        await session.commit()

        # Determine status
        if result.is_match and not result.needs_review:
            status = "validated"
        elif result.needs_review:
            status = "review"
        else:
            status = "rejected"

        return {
            "is_match": result.is_match,
            "confidence": float(result.confidence),
            "company_type": result.company_type,
            "needs_review": result.needs_review,
            "status": status,
            "reasoning": result.reasoning,
        }


@shared_task(
    name="app.workers.validation_tasks.batch_validate_campaign",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
)
def batch_validate_campaign(self, campaign_id: str, limit: int = 50) -> dict[str, int]:
    """
    Batch validate all pending contacts in a campaign.

    Args:
        campaign_id: UUID string of the campaign
        limit: Maximum contacts to process per batch

    Returns:
        Dict with counts: {'validated': N, 'rejected': M, 'review': R, 'errors': E}
    """
    try:
        return asyncio.get_event_loop().run_until_complete(
            _batch_validate_async(UUID(campaign_id), limit)
        )
    except RuntimeError:
        return asyncio.run(_batch_validate_async(UUID(campaign_id), limit))
    except Exception as e:
        logger.error(
            "batch_validation_task_failed",
            campaign_id=campaign_id,
            error=str(e),
        )
        raise self.retry(exc=e)


async def _batch_validate_async(campaign_id: UUID, limit: int) -> dict[str, int]:
    """Async implementation of batch validation."""
    async with async_session_factory() as session:
        service = CompanyValidationService(session)
        results = await service.batch_validate_contacts(campaign_id, limit)

        logger.info(
            "batch_validation_complete",
            campaign_id=str(campaign_id),
            validated=results["validated"],
            rejected=results["rejected"],
            review=results["review"],
            errors=results["errors"],
        )

        return results


@shared_task(
    name="app.workers.validation_tasks.validate_all_campaigns",
    bind=True,
    max_retries=1,
)
def validate_all_campaigns(self, limit_per_campaign: int = 25) -> dict[str, int]:
    """
    Process pending validations across all active campaigns.

    Scheduled task to run periodically (e.g., hourly) to validate
    new contacts added to campaigns.

    Args:
        limit_per_campaign: Max contacts to validate per campaign

    Returns:
        Dict with total counts across all campaigns
    """
    try:
        return asyncio.get_event_loop().run_until_complete(
            _validate_all_campaigns_async(limit_per_campaign)
        )
    except RuntimeError:
        return asyncio.run(_validate_all_campaigns_async(limit_per_campaign))
    except Exception as e:
        logger.error("validate_all_campaigns_failed", error=str(e))
        raise self.retry(exc=e)


async def _validate_all_campaigns_async(limit_per_campaign: int) -> dict[str, int]:
    """Async implementation of all-campaign validation."""
    from sqlalchemy import select

    from app.db.models.campaign import Campaign

    totals = {"validated": 0, "rejected": 0, "review": 0, "errors": 0, "campaigns": 0}

    async with async_session_factory() as session:
        # Get all active campaigns
        stmt = select(Campaign).where(
            Campaign.status == "active",
            Campaign.deleted_at.is_(None),
        )
        result = await session.execute(stmt)
        campaigns = result.scalars().all()

        for campaign in campaigns:
            try:
                service = CompanyValidationService(session)
                results = await service.batch_validate_contacts(
                    campaign.id, limit_per_campaign
                )
                totals["validated"] += results["validated"]
                totals["rejected"] += results["rejected"]
                totals["review"] += results["review"]
                totals["errors"] += results["errors"]
                totals["campaigns"] += 1
            except Exception as e:
                logger.error(
                    "campaign_validation_failed",
                    campaign_id=str(campaign.id),
                    error=str(e),
                )
                totals["errors"] += 1

    logger.info(
        "all_campaigns_validation_complete",
        campaigns_processed=totals["campaigns"],
        total_validated=totals["validated"],
        total_rejected=totals["rejected"],
        total_review=totals["review"],
    )

    return totals

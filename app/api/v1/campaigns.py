"""Campaign API endpoints for ROI tracking and management."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.api.v1.schemas import (
    CampaignCreate,
    CampaignListResponse,
    CampaignResponse,
    CampaignROIUpdate,
    MessageResponse,
)
from app.core.logging import get_logger
from app.db.models.campaign import Campaign
from app.dependencies import DbSession

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=CampaignListResponse)
async def list_campaigns(
    session: DbSession,
    status: str | None = Query(None, description="Filter by status"),
):
    """List all campaigns."""
    query = select(Campaign).where(Campaign.deleted_at.is_(None))

    if status:
        query = query.where(Campaign.status == status)

    query = query.order_by(Campaign.created_at.desc())

    result = await session.execute(query)
    campaigns = result.scalars().all()

    return CampaignListResponse(
        items=[CampaignResponse.model_validate(c) for c in campaigns],
        total=len(campaigns),
    )


@router.post("", response_model=CampaignResponse)
async def create_campaign(
    session: DbSession,
    campaign_data: CampaignCreate,
):
    """Create a new campaign."""
    campaign = Campaign(
        name=campaign_data.name,
        description=campaign_data.description,
        status=campaign_data.status,
        smartlead_campaign_id=campaign_data.smartlead_campaign_id,
        target_types=campaign_data.target_types,
        target_industries=campaign_data.target_industries,
        exclude_types=campaign_data.exclude_types,
        min_employees=campaign_data.min_employees,
        max_employees=campaign_data.max_employees,
        cost_per_email=campaign_data.cost_per_email,
        average_deal_value=campaign_data.average_deal_value,
    )

    session.add(campaign)
    await session.commit()
    await session.refresh(campaign)

    logger.info("campaign_created", campaign_id=str(campaign.id), name=campaign.name)

    return CampaignResponse.model_validate(campaign)


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    session: DbSession,
    campaign_id: UUID,
):
    """Get a specific campaign by ID."""
    result = await session.execute(
        select(Campaign)
        .where(Campaign.id == campaign_id)
        .where(Campaign.deleted_at.is_(None))
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return CampaignResponse.model_validate(campaign)


@router.patch("/{campaign_id}/roi", response_model=CampaignResponse)
async def update_campaign_roi(
    session: DbSession,
    campaign_id: UUID,
    roi_data: CampaignROIUpdate,
):
    """
    Update campaign ROI settings.

    Use this endpoint to:
    - Set cost per email for ROI calculation
    - Set average deal value for revenue projection
    - Update total emails sent counter
    """
    result = await session.execute(
        select(Campaign)
        .where(Campaign.id == campaign_id)
        .where(Campaign.deleted_at.is_(None))
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Update fields if provided
    if roi_data.cost_per_email is not None:
        campaign.cost_per_email = roi_data.cost_per_email
    if roi_data.average_deal_value is not None:
        campaign.average_deal_value = roi_data.average_deal_value
    if roi_data.total_emails_sent is not None:
        campaign.total_emails_sent = roi_data.total_emails_sent

    await session.commit()
    await session.refresh(campaign)

    logger.info(
        "campaign_roi_updated",
        campaign_id=str(campaign.id),
        cost_per_email=str(campaign.cost_per_email),
        average_deal_value=str(campaign.average_deal_value),
        total_emails_sent=campaign.total_emails_sent,
    )

    return CampaignResponse.model_validate(campaign)


@router.post("/{campaign_id}/increment-emails", response_model=MessageResponse)
async def increment_emails_sent(
    session: DbSession,
    campaign_id: UUID,
    count: int = Query(1, ge=1, description="Number of emails to add"),
):
    """
    Increment the emails sent counter for a campaign.

    Use this endpoint when emails are sent via SmartLead
    to keep the ROI calculations accurate.
    """
    result = await session.execute(
        select(Campaign)
        .where(Campaign.id == campaign_id)
        .where(Campaign.deleted_at.is_(None))
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign.total_emails_sent += count
    await session.commit()

    logger.info(
        "campaign_emails_incremented",
        campaign_id=str(campaign.id),
        added=count,
        total=campaign.total_emails_sent,
    )

    return MessageResponse(
        message=f"Added {count} emails. Total: {campaign.total_emails_sent}",
        success=True,
    )


@router.delete("/{campaign_id}", response_model=MessageResponse)
async def delete_campaign(
    session: DbSession,
    campaign_id: UUID,
):
    """Soft delete a campaign."""
    from datetime import datetime

    result = await session.execute(
        select(Campaign)
        .where(Campaign.id == campaign_id)
        .where(Campaign.deleted_at.is_(None))
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign.deleted_at = datetime.utcnow()
    await session.commit()

    logger.info("campaign_deleted", campaign_id=str(campaign.id))

    return MessageResponse(
        message=f"Campaign '{campaign.name}' deleted",
        success=True,
    )

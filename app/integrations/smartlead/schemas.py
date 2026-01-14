"""SmartLead API schemas."""

from pydantic import BaseModel


class SmartLeadLead(BaseModel):
    """SmartLead lead data."""

    id: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    company_name: str | None = None
    campaign_id: str | None = None
    status: str | None = None


class SmartLeadCampaign(BaseModel):
    """SmartLead campaign data."""

    id: str
    name: str
    status: str | None = None


class SmartLeadTagUpdate(BaseModel):
    """Request to update lead tags."""

    lead_id: str
    tags: list[str]

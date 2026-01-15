"""SmartLead.ai API client."""

from typing import Any

from app.config import settings
from app.core.exceptions import SmartLeadError
from app.core.logging import get_logger
from app.integrations.base import BaseClient

logger = get_logger(__name__)


class SmartLeadClient(BaseClient):
    """Client for SmartLead.ai API."""

    BASE_URL = "https://api.smartlead.ai/api/v1"

    def __init__(self):
        super().__init__(
            base_url=self.BASE_URL,
            api_key=settings.smartlead_api_key.get_secret_value(),
            integration_name="smartlead",
        )

    async def get_lead(self, lead_id: str) -> dict[str, Any]:
        """Get lead by ID."""
        try:
            return await self.get(f"/leads/{lead_id}")
        except Exception as e:
            raise SmartLeadError(f"Failed to get lead {lead_id}: {e}")

    async def get_lead_by_email(self, email: str) -> dict[str, Any] | None:
        """Get lead by email address."""
        try:
            response = await self.get("/leads", params={"email": email})
            leads = response.get("data", [])
            return leads[0] if leads else None
        except Exception as e:
            raise SmartLeadError(f"Failed to get lead by email {email}: {e}")

    async def update_lead_tags(self, lead_id: str, tags: list[str]) -> dict[str, Any]:
        """Update tags for a lead."""
        try:
            return await self.post(f"/leads/{lead_id}/tags", json={"tags": tags})
        except Exception as e:
            raise SmartLeadError(f"Failed to update tags for lead {lead_id}: {e}")

    async def update_lead_category(
        self,
        lead_id: str,
        category: str,
        subcategory: str,
    ) -> dict[str, Any]:
        """Update category for a lead."""
        try:
            return await self.patch(
                f"/leads/{lead_id}",
                json={
                    "category": category,
                    "subcategory": subcategory,
                },
            )
        except Exception as e:
            raise SmartLeadError(f"Failed to update category for lead {lead_id}: {e}")

    async def get_campaign(self, campaign_id: str) -> dict[str, Any]:
        """Get campaign by ID."""
        try:
            return await self.get(f"/campaigns/{campaign_id}")
        except Exception as e:
            raise SmartLeadError(f"Failed to get campaign {campaign_id}: {e}")

    async def add_lead_to_campaign(
        self,
        campaign_id: str,
        email: str,
        first_name: str | None = None,
        last_name: str | None = None,
        company_name: str | None = None,
        custom_fields: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Add a lead to a campaign."""
        try:
            payload = {
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "company_name": company_name,
                **(custom_fields or {}),
            }
            return await self.post(
                f"/campaigns/{campaign_id}/leads",
                json=payload,
            )
        except Exception as e:
            raise SmartLeadError(f"Failed to add lead to campaign {campaign_id}: {e}")

    async def get_campaigns(self, status: str | None = None) -> list[dict[str, Any]]:
        """Get all campaigns, optionally filtered by status."""
        try:
            params = {}
            if status:
                params["status"] = status
            response = await self.get("/campaigns", params=params)
            return response.get("data", [])
        except Exception as e:
            raise SmartLeadError(f"Failed to get campaigns: {e}")

    async def create_lead(
        self,
        email: str,
        first_name: str | None = None,
        last_name: str | None = None,
        company_name: str | None = None,
        phone: str | None = None,
        linkedin_url: str | None = None,
        custom_fields: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Create a new lead in SmartLead."""
        try:
            payload = {
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "company_name": company_name,
                "phone": phone,
                "linkedin_url": linkedin_url,
                **(custom_fields or {}),
            }
            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}
            return await self.post("/leads", json=payload)
        except Exception as e:
            raise SmartLeadError(f"Failed to create lead: {e}")

    async def remove_lead_from_campaign(
        self,
        campaign_id: str,
        lead_id: str,
    ) -> dict[str, Any]:
        """Remove a lead from a campaign."""
        try:
            return await self.delete(f"/campaigns/{campaign_id}/leads/{lead_id}")
        except Exception as e:
            raise SmartLeadError(f"Failed to remove lead {lead_id} from campaign {campaign_id}: {e}")

    async def get_campaign_leads(
        self,
        campaign_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get leads in a campaign."""
        try:
            response = await self.get(
                f"/campaigns/{campaign_id}/leads",
                params={"limit": limit, "offset": offset},
            )
            return response.get("data", [])
        except Exception as e:
            raise SmartLeadError(f"Failed to get leads for campaign {campaign_id}: {e}")

    async def add_to_blocklist(self, email: str) -> dict[str, Any]:
        """
        Add email to global blocklist (master suppression list).

        This ensures the email is never contacted again across ALL campaigns.
        Use for unsubscribes and hard bounces.
        """
        try:
            return await self.post(
                "/email-accounts/block-list",
                json={"email": email},
            )
        except Exception as e:
            raise SmartLeadError(f"Failed to add {email} to blocklist: {e}")

    async def get_lead_campaigns(self, email: str) -> list[dict[str, Any]]:
        """
        Get all campaigns a lead is enrolled in by their email.

        Returns list of campaign objects the lead is part of.
        """
        try:
            lead = await self.get_lead_by_email(email)
            if not lead:
                return []

            # SmartLead stores campaign associations in lead data
            return lead.get("campaigns", [])
        except Exception as e:
            raise SmartLeadError(f"Failed to get campaigns for {email}: {e}")

    async def remove_lead_from_all_campaigns(self, email: str) -> dict[str, Any]:
        """
        Remove a lead from all campaigns by email.

        Used when we don't have the specific campaign_id but need to suppress.
        """
        try:
            lead = await self.get_lead_by_email(email)
            if not lead:
                return {"status": "not_found", "email": email}

            lead_id = lead.get("id")
            campaigns = lead.get("campaigns", [])

            removed_from = []
            errors = []

            for campaign in campaigns:
                campaign_id = campaign.get("id")
                if campaign_id:
                    try:
                        await self.remove_lead_from_campaign(campaign_id, lead_id)
                        removed_from.append(campaign_id)
                    except SmartLeadError as e:
                        errors.append({"campaign_id": campaign_id, "error": str(e)})

            return {
                "status": "completed",
                "email": email,
                "lead_id": lead_id,
                "removed_from_campaigns": removed_from,
                "errors": errors if errors else None,
            }
        except Exception as e:
            raise SmartLeadError(f"Failed to remove {email} from all campaigns: {e}")

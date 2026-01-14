"""HubSpot Deals API."""

from decimal import Decimal
from typing import Any

from app.config import settings
from app.core.exceptions import HubSpotError
from app.core.logging import get_logger
from app.integrations.hubspot.client import HubSpotClient

logger = get_logger(__name__)


class HubSpotDeals:
    """HubSpot Deals API wrapper."""

    # Common deal stages
    STAGE_APPOINTMENT_SCHEDULED = "appointmentscheduled"
    STAGE_QUALIFIED = "qualifiedtobuy"
    STAGE_PRESENTATION = "presentationscheduled"
    STAGE_DECISION_MAKER = "decisionmakerboughtin"
    STAGE_CONTRACT_SENT = "contractsent"
    STAGE_CLOSED_WON = "closedwon"
    STAGE_CLOSED_LOST = "closedlost"

    def __init__(self, client: HubSpotClient | None = None):
        self.client = client or HubSpotClient()

    async def create_deal(
        self,
        deal_name: str,
        pipeline_id: str | None = None,
        stage: str | None = None,
        amount: Decimal | None = None,
        close_date: str | None = None,
        owner_id: str | None = None,
        contact_id: str | None = None,
        company_id: str | None = None,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new deal in HubSpot.

        Args:
            deal_name: Name of the deal
            pipeline_id: Pipeline ID (uses default if not provided)
            stage: Deal stage (uses first stage if not provided)
            amount: Deal amount
            close_date: Expected close date (YYYY-MM-DD format)
            owner_id: HubSpot user ID for deal owner
            contact_id: HubSpot contact ID to associate
            company_id: HubSpot company ID to associate
            properties: Additional properties

        Returns:
            Created deal data
        """
        try:
            payload_properties = {
                "dealname": deal_name,
                **(properties or {}),
            }

            if pipeline_id:
                payload_properties["pipeline"] = pipeline_id

            if stage:
                payload_properties["dealstage"] = stage

            if amount is not None:
                payload_properties["amount"] = str(amount)

            if close_date:
                payload_properties["closedate"] = close_date

            if owner_id:
                payload_properties["hubspot_owner_id"] = owner_id
            elif settings.hubspot_owner_id:
                payload_properties["hubspot_owner_id"] = settings.hubspot_owner_id

            payload: dict[str, Any] = {
                "properties": payload_properties,
            }

            # Add associations
            associations = []
            if contact_id:
                associations.append({
                    "to": {"id": contact_id},
                    "types": [
                        {
                            "associationCategory": "HUBSPOT_DEFINED",
                            "associationTypeId": 3,  # Deal to Contact
                        }
                    ],
                })

            if company_id:
                associations.append({
                    "to": {"id": company_id},
                    "types": [
                        {
                            "associationCategory": "HUBSPOT_DEFINED",
                            "associationTypeId": 5,  # Deal to Company
                        }
                    ],
                })

            if associations:
                payload["associations"] = associations

            response = await self.client.post(
                "/crm/v3/objects/deals",
                json=payload,
            )

            logger.info(
                "deal_created",
                deal_id=response.get("id"),
                deal_name=deal_name,
                stage=stage,
            )

            return response

        except Exception as e:
            logger.error(
                "create_deal_failed",
                deal_name=deal_name,
                error=str(e),
            )
            raise HubSpotError(f"Failed to create deal: {e}")

    async def get_deal(self, deal_id: str) -> dict[str, Any]:
        """Get deal by ID."""
        try:
            return await self.client.get(f"/crm/v3/objects/deals/{deal_id}")
        except Exception as e:
            raise HubSpotError(f"Failed to get deal {deal_id}: {e}")

    async def update_deal(
        self,
        deal_id: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Update a deal in HubSpot.

        Args:
            deal_id: HubSpot deal ID
            properties: Properties to update

        Returns:
            Updated deal data
        """
        try:
            response = await self.client.patch(
                f"/crm/v3/objects/deals/{deal_id}",
                json={"properties": properties},
            )

            logger.info(
                "deal_updated",
                deal_id=deal_id,
            )

            return response

        except Exception as e:
            logger.error(
                "update_deal_failed",
                deal_id=deal_id,
                error=str(e),
            )
            raise HubSpotError(f"Failed to update deal {deal_id}: {e}")

    async def update_deal_stage(
        self,
        deal_id: str,
        stage: str,
        pipeline_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Update deal stage in pipeline.

        Args:
            deal_id: HubSpot deal ID
            stage: New deal stage
            pipeline_id: Pipeline ID (if changing pipeline)

        Returns:
            Updated deal data
        """
        properties = {"dealstage": stage}
        if pipeline_id:
            properties["pipeline"] = pipeline_id

        return await self.update_deal(deal_id, properties)

    async def close_deal_won(
        self,
        deal_id: str,
        amount: Decimal | None = None,
        close_date: str | None = None,
    ) -> dict[str, Any]:
        """
        Mark a deal as closed won.

        Args:
            deal_id: HubSpot deal ID
            amount: Final deal amount
            close_date: Actual close date

        Returns:
            Updated deal data
        """
        from datetime import date

        properties: dict[str, Any] = {"dealstage": self.STAGE_CLOSED_WON}

        if amount is not None:
            properties["amount"] = str(amount)

        if close_date:
            properties["closedate"] = close_date
        else:
            properties["closedate"] = date.today().isoformat()

        return await self.update_deal(deal_id, properties)

    async def close_deal_lost(
        self,
        deal_id: str,
        close_date: str | None = None,
        lost_reason: str | None = None,
    ) -> dict[str, Any]:
        """
        Mark a deal as closed lost.

        Args:
            deal_id: HubSpot deal ID
            close_date: Actual close date
            lost_reason: Reason for losing the deal

        Returns:
            Updated deal data
        """
        from datetime import date

        properties: dict[str, Any] = {"dealstage": self.STAGE_CLOSED_LOST}

        if close_date:
            properties["closedate"] = close_date
        else:
            properties["closedate"] = date.today().isoformat()

        if lost_reason:
            properties["closed_lost_reason"] = lost_reason

        return await self.update_deal(deal_id, properties)

    async def get_pipelines(self) -> list[dict[str, Any]]:
        """Get all deal pipelines."""
        try:
            response = await self.client.get("/crm/v3/pipelines/deals")
            return response.get("results", [])
        except Exception as e:
            raise HubSpotError(f"Failed to get pipelines: {e}")

    async def get_pipeline_stages(
        self,
        pipeline_id: str,
    ) -> list[dict[str, Any]]:
        """
        Get stages for a specific pipeline.

        Args:
            pipeline_id: Pipeline ID

        Returns:
            List of stage data
        """
        try:
            response = await self.client.get(f"/crm/v3/pipelines/deals/{pipeline_id}")
            return response.get("stages", [])
        except Exception as e:
            raise HubSpotError(f"Failed to get pipeline stages: {e}")

    async def get_contact_deals(
        self,
        contact_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get deals associated with a contact.

        Args:
            contact_id: HubSpot contact ID
            limit: Maximum number of deals to return

        Returns:
            List of deal data
        """
        try:
            response = await self.client.get(
                f"/crm/v3/objects/contacts/{contact_id}/associations/deals",
            )

            deal_ids = [
                assoc.get("id") for assoc in response.get("results", [])[:limit]
            ]

            deals = []
            for deal_id in deal_ids:
                try:
                    deal = await self.get_deal(deal_id)
                    deals.append(deal)
                except Exception:
                    continue

            return deals

        except Exception as e:
            logger.error(
                "get_contact_deals_failed",
                contact_id=contact_id,
                error=str(e),
            )
            raise HubSpotError(f"Failed to get deals for contact {contact_id}: {e}")

    async def search_deals(
        self,
        filters: list[dict[str, Any]],
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Search deals with filters.

        Args:
            filters: List of filter objects
            limit: Maximum results to return

        Returns:
            List of matching deals
        """
        try:
            response = await self.client.post(
                "/crm/v3/objects/deals/search",
                json={
                    "filterGroups": [{"filters": filters}],
                    "limit": limit,
                },
            )
            return response.get("results", [])
        except Exception as e:
            raise HubSpotError(f"Failed to search deals: {e}")

    def get_deal_url(self, deal_id: str) -> str:
        """Get the HubSpot URL for a deal."""
        portal_id = settings.hubspot_portal_id
        if portal_id:
            return f"https://app.hubspot.com/contacts/{portal_id}/deal/{deal_id}"
        return f"https://app.hubspot.com/deal/{deal_id}"

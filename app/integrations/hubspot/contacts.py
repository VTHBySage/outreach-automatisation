"""HubSpot Contacts API."""

from typing import Any

from app.core.exceptions import HubSpotError
from app.core.logging import get_logger
from app.integrations.hubspot.client import HubSpotClient

logger = get_logger(__name__)


class HubSpotContacts:
    """HubSpot Contacts API wrapper."""

    def __init__(self, client: HubSpotClient | None = None):
        self.client = client or HubSpotClient()

    async def create_contact(
        self,
        email: str,
        first_name: str | None = None,
        last_name: str | None = None,
        company: str | None = None,
        phone: str | None = None,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new contact in HubSpot."""
        try:
            # Build properties dict, filtering out None values (HubSpot rejects nulls)
            props = {
                "email": email,
                "firstname": first_name,
                "lastname": last_name,
                "company": company,
                "phone": phone,
                **(properties or {}),
            }
            # Filter out None values
            payload = {
                "properties": {k: v for k, v in props.items() if v is not None}
            }
            return await self.client.post("/crm/v3/objects/contacts", json=payload)
        except Exception as e:
            raise HubSpotError(f"Failed to create contact: {e}")

    async def get_contact_by_email(self, email: str) -> dict[str, Any] | None:
        """Get contact by email address."""
        try:
            response = await self.client.post(
                "/crm/v3/objects/contacts/search",
                json={
                    "filterGroups": [
                        {
                            "filters": [
                                {
                                    "propertyName": "email",
                                    "operator": "EQ",
                                    "value": email,
                                }
                            ]
                        }
                    ]
                },
            )
            results = response.get("results", [])
            return results[0] if results else None
        except Exception as e:
            raise HubSpotError(f"Failed to get contact by email: {e}")

    async def update_contact(
        self,
        contact_id: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """Update contact properties."""
        try:
            return await self.client.patch(
                f"/crm/v3/objects/contacts/{contact_id}",
                json={"properties": properties},
            )
        except Exception as e:
            raise HubSpotError(f"Failed to update contact {contact_id}: {e}")

    async def get_or_create_contact(
        self,
        email: str,
        first_name: str | None = None,
        last_name: str | None = None,
        company: str | None = None,
        phone: str | None = None,
    ) -> dict[str, Any]:
        """Get existing contact or create new one."""
        existing = await self.get_contact_by_email(email)
        if existing:
            return existing
        return await self.create_contact(
            email=email,
            first_name=first_name,
            last_name=last_name,
            company=company,
            phone=phone,
        )

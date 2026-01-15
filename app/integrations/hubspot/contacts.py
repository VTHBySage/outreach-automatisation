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

    # Custom Property Management (Requirements.md 4.2.2)

    async def get_property(self, property_name: str) -> dict[str, Any] | None:
        """
        Get a contact property definition.

        Args:
            property_name: Internal name of the property (e.g., "validation_status")

        Returns:
            Property definition dict or None if not found
        """
        try:
            return await self.client.get(
                f"/crm/v3/properties/contacts/{property_name}"
            )
        except Exception as e:
            if "404" in str(e):
                return None
            raise HubSpotError(f"Failed to get property {property_name}: {e}")

    async def create_property(
        self,
        name: str,
        label: str,
        property_type: str = "string",
        field_type: str = "text",
        group_name: str = "contactinformation",
        description: str | None = None,
        options: list[dict] | None = None,
    ) -> dict[str, Any]:
        """
        Create a custom contact property.

        Args:
            name: Internal property name (e.g., "validation_status")
            label: Display label (e.g., "Validation Status")
            property_type: "string", "number", "date", "datetime", "enumeration"
            field_type: "text", "textarea", "date", "file", "number", "select", "radio", "checkbox"
            group_name: Property group (default "contactinformation")
            description: Optional property description
            options: For enumeration type, list of {"label": "...", "value": "..."}

        Returns:
            Created property definition
        """
        try:
            payload = {
                "name": name,
                "label": label,
                "type": property_type,
                "fieldType": field_type,
                "groupName": group_name,
            }
            if description:
                payload["description"] = description
            if options and property_type == "enumeration":
                payload["options"] = options

            return await self.client.post(
                "/crm/v3/properties/contacts",
                json=payload,
            )
        except Exception as e:
            raise HubSpotError(f"Failed to create property {name}: {e}")

    async def update_property(
        self,
        property_name: str,
        label: str | None = None,
        description: str | None = None,
        options: list[dict] | None = None,
    ) -> dict[str, Any]:
        """
        Update an existing contact property.

        Args:
            property_name: Internal name of property to update
            label: New display label
            description: New description
            options: New options for enumeration type

        Returns:
            Updated property definition
        """
        try:
            payload = {}
            if label:
                payload["label"] = label
            if description:
                payload["description"] = description
            if options:
                payload["options"] = options

            if not payload:
                raise HubSpotError("No update data provided")

            return await self.client.patch(
                f"/crm/v3/properties/contacts/{property_name}",
                json=payload,
            )
        except Exception as e:
            raise HubSpotError(f"Failed to update property {property_name}: {e}")

    async def get_all_properties(self) -> list[dict[str, Any]]:
        """Get all contact properties."""
        try:
            response = await self.client.get("/crm/v3/properties/contacts")
            return response.get("results", [])
        except Exception as e:
            raise HubSpotError(f"Failed to get properties: {e}")

    async def ensure_property_exists(
        self,
        name: str,
        label: str,
        property_type: str = "string",
        field_type: str = "text",
        options: list[dict] | None = None,
    ) -> dict[str, Any]:
        """
        Ensure a property exists, creating it if necessary.

        Args:
            name: Internal property name
            label: Display label
            property_type: Property type
            field_type: Field type
            options: Options for enumeration

        Returns:
            Property definition (existing or newly created)
        """
        existing = await self.get_property(name)
        if existing:
            logger.debug("property_exists", property_name=name)
            return existing

        logger.info("creating_property", property_name=name, label=label)
        return await self.create_property(
            name=name,
            label=label,
            property_type=property_type,
            field_type=field_type,
            options=options,
        )

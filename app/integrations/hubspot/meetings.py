"""HubSpot Meetings API."""

from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote

from app.config import settings
from app.core.exceptions import HubSpotError
from app.core.logging import get_logger
from app.integrations.hubspot.client import HubSpotClient

logger = get_logger(__name__)


class HubSpotMeetings:
    """HubSpot Meetings API wrapper."""

    # Default meeting duration in minutes
    DEFAULT_DURATION = 30

    def __init__(self, client: HubSpotClient | None = None):
        self.client = client or HubSpotClient()

    async def get_meeting_link(
        self,
        owner_id: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Get the meeting scheduling link for an owner.

        Args:
            owner_id: HubSpot user ID. If not provided, uses the configured default.

        Returns:
            Meeting link info or None if not found
        """
        try:
            # Get meeting links for the owner
            user_id = owner_id or settings.hubspot_owner_id
            response = await self.client.get(
                "/scheduler/v3/meetings/meeting-links",
                params={"userId": user_id} if user_id else {},
            )

            links = response.get("results", [])
            if links:
                # Return the first active meeting link
                for link in links:
                    if link.get("isActive", True):
                        return {
                            "id": link.get("id"),
                            "name": link.get("name"),
                            "link": link.get("link"),
                            "slug": link.get("slug"),
                            "duration": link.get("defaultDuration"),
                        }

            return None

        except Exception as e:
            logger.error("get_meeting_link_failed", error=str(e))
            raise HubSpotError(f"Failed to get meeting link: {e}")

    async def create_meeting(
        self,
        contact_id: str,
        title: str,
        start_time: datetime,
        duration_minutes: int = DEFAULT_DURATION,
        owner_id: str | None = None,
        description: str | None = None,
        meeting_outcome: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a meeting engagement in HubSpot.

        Args:
            contact_id: HubSpot contact ID to associate the meeting with
            title: Meeting title
            start_time: Meeting start time
            duration_minutes: Meeting duration in minutes
            owner_id: HubSpot user ID for the meeting owner
            description: Meeting description/agenda
            meeting_outcome: Meeting outcome (SCHEDULED, COMPLETED, RESCHEDULED, etc.)

        Returns:
            Created meeting data
        """
        try:
            end_time = start_time + timedelta(minutes=duration_minutes)

            payload = {
                "properties": {
                    "hs_timestamp": int(start_time.timestamp() * 1000),
                    "hs_meeting_title": title,
                    "hs_meeting_start_time": start_time.isoformat(),
                    "hs_meeting_end_time": end_time.isoformat(),
                },
                "associations": [
                    {
                        "to": {"id": contact_id},
                        "types": [
                            {
                                "associationCategory": "HUBSPOT_DEFINED",
                                "associationTypeId": 200,  # Meeting to Contact
                            }
                        ],
                    }
                ],
            }

            if owner_id:
                payload["properties"]["hubspot_owner_id"] = owner_id
            elif settings.hubspot_owner_id:
                payload["properties"]["hubspot_owner_id"] = settings.hubspot_owner_id

            if description:
                payload["properties"]["hs_meeting_body"] = description

            if meeting_outcome:
                payload["properties"]["hs_meeting_outcome"] = meeting_outcome

            response = await self.client.post(
                "/crm/v3/objects/meetings",
                json=payload,
            )

            logger.info(
                "meeting_created",
                meeting_id=response.get("id"),
                contact_id=contact_id,
                start_time=start_time.isoformat(),
            )

            return response

        except Exception as e:
            logger.error(
                "create_meeting_failed",
                contact_id=contact_id,
                error=str(e),
            )
            raise HubSpotError(f"Failed to create meeting: {e}")

    async def update_meeting(
        self,
        meeting_id: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Update a meeting in HubSpot.

        Args:
            meeting_id: HubSpot meeting ID
            properties: Properties to update

        Returns:
            Updated meeting data
        """
        try:
            response = await self.client.patch(
                f"/crm/v3/objects/meetings/{meeting_id}",
                json={"properties": properties},
            )

            logger.info(
                "meeting_updated",
                meeting_id=meeting_id,
            )

            return response

        except Exception as e:
            logger.error(
                "update_meeting_failed",
                meeting_id=meeting_id,
                error=str(e),
            )
            raise HubSpotError(f"Failed to update meeting {meeting_id}: {e}")

    async def get_meeting(self, meeting_id: str) -> dict[str, Any]:
        """Get meeting by ID."""
        try:
            return await self.client.get(f"/crm/v3/objects/meetings/{meeting_id}")
        except Exception as e:
            raise HubSpotError(f"Failed to get meeting {meeting_id}: {e}")

    async def get_contact_meetings(
        self,
        contact_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get meetings associated with a contact.

        Args:
            contact_id: HubSpot contact ID
            limit: Maximum number of meetings to return

        Returns:
            List of meeting data
        """
        try:
            response = await self.client.get(
                f"/crm/v3/objects/contacts/{contact_id}/associations/meetings",
            )

            meeting_ids = [
                assoc.get("id") for assoc in response.get("results", [])[:limit]
            ]

            meetings = []
            for meeting_id in meeting_ids:
                try:
                    meeting = await self.get_meeting(meeting_id)
                    meetings.append(meeting)
                except Exception:
                    continue

            return meetings

        except Exception as e:
            logger.error(
                "get_contact_meetings_failed",
                contact_id=contact_id,
                error=str(e),
            )
            raise HubSpotError(f"Failed to get meetings for contact {contact_id}: {e}")

    async def schedule_meeting_with_link(
        self,
        contact_id: str,
        contact_email: str,
        contact_name: str,
        meeting_link_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate a scheduling link for a contact.

        This creates a personalized booking link that the contact can use
        to schedule a meeting at their convenience.

        Args:
            contact_id: HubSpot contact ID
            contact_email: Contact's email address
            contact_name: Contact's name
            meeting_link_id: Specific meeting link ID to use

        Returns:
            Scheduling link info
        """
        try:
            # Get the meeting link
            if meeting_link_id:
                meeting_link = await self.client.get(
                    f"/scheduler/v3/meetings/meeting-links/{meeting_link_id}"
                )
            else:
                meeting_link = await self.get_meeting_link()

            if not meeting_link:
                raise HubSpotError("No meeting link available")

            # Build the personalized booking URL
            base_url = meeting_link.get("link", "")
            if base_url:
                # Add contact info as query params for prefilling
                # URL-encode values to handle special characters
                encoded_email = quote(contact_email, safe="")
                encoded_name = quote(contact_name, safe="")
                booking_url = f"{base_url}?email={encoded_email}&name={encoded_name}"
            else:
                booking_url = None

            return {
                "meeting_link_id": meeting_link.get("id"),
                "meeting_link_name": meeting_link.get("name"),
                "booking_url": booking_url,
                "duration_minutes": meeting_link.get("duration", self.DEFAULT_DURATION),
            }

        except HubSpotError:
            raise
        except Exception as e:
            logger.error(
                "schedule_meeting_with_link_failed",
                contact_id=contact_id,
                error=str(e),
            )
            raise HubSpotError(f"Failed to generate scheduling link: {e}")

    def get_meeting_url(self, meeting_id: str) -> str:
        """Get the HubSpot URL for a meeting."""
        portal_id = settings.hubspot_portal_id
        if portal_id:
            return f"https://app.hubspot.com/contacts/{portal_id}/record/0-47/{meeting_id}"
        return f"https://app.hubspot.com/record/0-47/{meeting_id}"

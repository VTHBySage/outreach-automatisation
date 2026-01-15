"""HubSpot Notes/Engagements API."""

from datetime import datetime
from typing import Any

from app.core.exceptions import HubSpotError
from app.core.logging import get_logger
from app.integrations.hubspot.client import HubSpotClient

logger = get_logger(__name__)


class HubSpotNotes:
    """HubSpot Notes API wrapper for adding notes to contacts."""

    def __init__(self, client: HubSpotClient | None = None):
        self.client = client or HubSpotClient()

    async def create_note(
        self,
        contact_id: str,
        body: str,
        timestamp: datetime | None = None,
        owner_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a note and associate it with a contact.

        Args:
            contact_id: HubSpot contact ID to associate note with
            body: Note content/body text
            timestamp: When the note was created (defaults to now)
            owner_id: HubSpot owner ID (optional)

        Returns:
            Created note object with id and properties

        Raises:
            HubSpotError: If note creation fails
        """
        try:
            # Build note properties
            note_timestamp = timestamp or datetime.utcnow()
            properties: dict[str, Any] = {
                "hs_note_body": body,
                "hs_timestamp": int(note_timestamp.timestamp() * 1000),
            }
            if owner_id:
                properties["hubspot_owner_id"] = owner_id

            # Create the note object
            note_response = await self.client.post(
                "/crm/v3/objects/notes",
                json={"properties": properties},
            )
            note_id = note_response.get("id")

            if not note_id:
                raise HubSpotError("Note created but no ID returned")

            # Associate note with contact
            await self._associate_note_with_contact(note_id, contact_id)

            logger.info(
                "hubspot_note_created",
                note_id=note_id,
                contact_id=contact_id,
            )

            return note_response
        except HubSpotError:
            raise
        except Exception as e:
            raise HubSpotError(f"Failed to create note for contact {contact_id}: {e}")

    async def _associate_note_with_contact(
        self,
        note_id: str,
        contact_id: str,
    ) -> None:
        """Associate a note with a contact using HubSpot associations API."""
        try:
            # HubSpot v4 associations API
            await self.client.put(
                f"/crm/v4/objects/notes/{note_id}/associations/contacts/{contact_id}",
                json=[
                    {
                        "associationCategory": "HUBSPOT_DEFINED",
                        "associationTypeId": 190,  # Note to Contact association type
                    }
                ],
            )
        except Exception as e:
            raise HubSpotError(
                f"Failed to associate note {note_id} with contact {contact_id}: {e}"
            )

    async def get_contact_notes(
        self,
        contact_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Get all notes associated with a contact.

        Args:
            contact_id: HubSpot contact ID
            limit: Maximum notes to return

        Returns:
            List of note objects with id, body, timestamp

        Raises:
            HubSpotError: If fetching notes fails
        """
        try:
            # Get associated note IDs
            associations_response = await self.client.get(
                f"/crm/v4/objects/contacts/{contact_id}/associations/notes",
            )

            note_ids = [
                result.get("toObjectId")
                for result in associations_response.get("results", [])
                if result.get("toObjectId")
            ]

            if not note_ids:
                return []

            # Batch read notes (up to limit)
            note_ids = note_ids[:limit]
            notes_response = await self.client.post(
                "/crm/v3/objects/notes/batch/read",
                json={
                    "inputs": [{"id": nid} for nid in note_ids],
                    "properties": ["hs_note_body", "hs_timestamp", "hubspot_owner_id"],
                },
            )

            return notes_response.get("results", [])
        except Exception as e:
            raise HubSpotError(f"Failed to get notes for contact {contact_id}: {e}")

    async def delete_note(self, note_id: str) -> None:
        """
        Delete a note by ID.

        Args:
            note_id: HubSpot note ID to delete

        Raises:
            HubSpotError: If deletion fails
        """
        try:
            await self.client.delete(f"/crm/v3/objects/notes/{note_id}")
            logger.info("hubspot_note_deleted", note_id=note_id)
        except Exception as e:
            raise HubSpotError(f"Failed to delete note {note_id}: {e}")

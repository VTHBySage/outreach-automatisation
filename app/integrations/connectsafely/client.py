"""ConnectSafely API client for LinkedIn messaging."""

from typing import Any

from app.config import settings
from app.core.exceptions import ConnectSafelyError
from app.core.logging import get_logger
from app.integrations.base import BaseClient

logger = get_logger(__name__)


class ConnectSafelyClient(BaseClient):
    """Client for ConnectSafely LinkedIn messaging API."""

    BASE_URL = "https://api.connectsafely.com/v1"

    def __init__(self):
        super().__init__(
            base_url=self.BASE_URL,
            api_key=settings.connectsafely_api_key.get_secret_value(),
        )

    async def find_profile_by_email(self, email: str) -> dict[str, Any] | None:
        """Find LinkedIn profile by email address."""
        try:
            response = await self.post(
                "/profiles/search",
                json={"email": email},
            )
            profiles = response.get("profiles", [])
            return profiles[0] if profiles else None
        except Exception as e:
            raise ConnectSafelyError(f"Failed to find profile by email: {e}")

    async def send_connection_request(
        self,
        profile_url: str,
        message: str | None = None,
    ) -> dict[str, Any]:
        """Send LinkedIn connection request."""
        try:
            payload: dict[str, Any] = {"profile_url": profile_url}
            if message:
                payload["message"] = message

            return await self.post("/connections/request", json=payload)
        except Exception as e:
            raise ConnectSafelyError(f"Failed to send connection request: {e}")

    async def send_direct_message(
        self,
        profile_url: str,
        message: str,
    ) -> dict[str, Any]:
        """Send LinkedIn direct message (requires connection)."""
        try:
            return await self.post(
                "/messages/send",
                json={
                    "profile_url": profile_url,
                    "message": message,
                },
            )
        except Exception as e:
            raise ConnectSafelyError(f"Failed to send DM: {e}")

    async def get_connection_status(self, profile_url: str) -> str:
        """Get connection status with a profile."""
        try:
            response = await self.get(
                "/connections/status",
                params={"profile_url": profile_url},
            )
            return response.get("status", "unknown")
        except Exception as e:
            raise ConnectSafelyError(f"Failed to get connection status: {e}")

    async def get_pending_messages(self) -> list[dict[str, Any]]:
        """Get pending/draft messages awaiting approval."""
        try:
            response = await self.get("/messages/pending")
            return response.get("messages", [])
        except Exception as e:
            raise ConnectSafelyError(f"Failed to get pending messages: {e}")

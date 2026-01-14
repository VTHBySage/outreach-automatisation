"""HubSpot API client."""

from app.config import settings
from app.integrations.base import BaseClient


class HubSpotClient(BaseClient):
    """Base client for HubSpot API."""

    def __init__(self):
        super().__init__(
            base_url=settings.hubspot_api_base_url,
            api_key=settings.hubspot_access_token.get_secret_value(),
        )

    def _get_default_headers(self) -> dict[str, str]:
        """Get default headers with HubSpot auth."""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

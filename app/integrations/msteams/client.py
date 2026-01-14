"""MS Teams webhook client."""

from typing import Any
from uuid import uuid4

import httpx

from app.config import settings
from app.core.exceptions import NotificationError
from app.core.logging import get_logger

logger = get_logger(__name__)


class MSTeamsClient:
    """Client for sending MS Teams webhook notifications."""

    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or settings.msteams_webhook_url
        self.timeout = 30.0

    async def send_message(self, card: dict[str, Any]) -> str:
        """
        Send adaptive card message to MS Teams channel.

        Args:
            card: Adaptive card JSON structure

        Returns:
            Message ID (generated, as Teams webhooks don't return IDs)

        Raises:
            NotificationError: If sending fails
        """
        if not self.webhook_url:
            raise NotificationError("MS Teams webhook URL not configured")

        message_id = str(uuid4())

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.webhook_url, json=card)
                response.raise_for_status()

            logger.info(
                "teams_message_sent",
                message_id=message_id,
                status_code=response.status_code,
            )

            return message_id

        except httpx.HTTPStatusError as e:
            logger.error(
                "teams_message_failed",
                message_id=message_id,
                status_code=e.response.status_code,
                response_text=e.response.text[:500],
            )
            raise NotificationError(f"Teams webhook failed: {e.response.status_code}")

        except httpx.RequestError as e:
            logger.error(
                "teams_request_failed",
                message_id=message_id,
                error=str(e),
            )
            raise NotificationError(f"Teams request failed: {e}")

    async def send_simple_message(self, text: str) -> str:
        """Send a simple text message to MS Teams."""
        card = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "text": text,
        }
        return await self.send_message(card)

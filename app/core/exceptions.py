"""Custom application exceptions."""

from typing import Any


class OutreachError(Exception):
    """Base exception for the application."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class WebhookError(OutreachError):
    """Webhook processing error."""

    pass


class WebhookSignatureError(WebhookError):
    """Invalid webhook signature."""

    pass


class CategorizationError(OutreachError):
    """AI categorization error."""

    pass


class IntegrationError(OutreachError):
    """External service integration error."""

    pass


class RateLimitError(IntegrationError):
    """Rate limit exceeded error with retry information."""

    def __init__(
        self,
        message: str,
        retry_after: int | None = None,
        details: dict | None = None,
    ):
        super().__init__(message, details)
        self.retry_after = retry_after  # Seconds to wait before retrying


class HubSpotError(IntegrationError):
    """HubSpot API error."""

    pass


class SmartLeadError(IntegrationError):
    """SmartLead API error."""

    pass


class ApolloError(IntegrationError):
    """Apollo API error."""

    pass


class ConnectSafelyError(IntegrationError):
    """ConnectSafely API error."""

    pass


class OpenAIError(IntegrationError):
    """OpenAI API error."""

    pass


class TaskCreationError(OutreachError):
    """Task creation error."""

    pass


class NotificationError(OutreachError):
    """Notification sending error."""

    pass


class ValidationError(OutreachError):
    """Data validation error."""

    pass


class NotFoundError(OutreachError):
    """Resource not found error."""

    pass

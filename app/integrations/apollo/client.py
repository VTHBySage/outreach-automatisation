"""Apollo.io API client."""

from typing import Any

from app.config import settings
from app.core.exceptions import ApolloError
from app.core.logging import get_logger
from app.integrations.base import BaseClient

logger = get_logger(__name__)


class ApolloClient(BaseClient):
    """Client for Apollo.io API."""

    BASE_URL = "https://api.apollo.io/v1"

    def __init__(self):
        api_key = settings.apollo_api_key.get_secret_value()
        if not api_key:
            logger.warning("apollo_api_key_not_configured")
        super().__init__(
            base_url=self.BASE_URL,
            api_key=api_key,
            integration_name="apollo",
        )

    def _get_default_headers(self) -> dict[str, str]:
        """Get default headers with Apollo auth."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        return headers

    async def search_people(
        self,
        email: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        organization_name: str | None = None,
        domain: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search for people in Apollo."""
        try:
            params: dict[str, Any] = {}
            if email:
                params["email"] = email
            if first_name:
                params["first_name"] = first_name
            if last_name:
                params["last_name"] = last_name
            if organization_name:
                params["organization_name"] = organization_name
            if domain:
                params["organization_domains"] = [domain]

            response = await self.post("/people/search", json=params)
            return response.get("people", [])
        except Exception as e:
            raise ApolloError(f"Failed to search people: {e}")

    async def enrich_person(self, email: str) -> dict[str, Any] | None:
        """Enrich person data by email."""
        try:
            response = await self.post(
                "/people/match",
                json={"email": email, "reveal_personal_emails": True},
            )
            return response.get("person")
        except Exception as e:
            raise ApolloError(f"Failed to enrich person {email}: {e}")

    async def enrich_organization(self, domain: str) -> dict[str, Any] | None:
        """Enrich organization data by domain."""
        try:
            response = await self.post(
                "/organizations/match",
                json={"domain": domain},
            )
            return response.get("organization")
        except Exception as e:
            raise ApolloError(f"Failed to enrich organization {domain}: {e}")

    async def get_contact_info(
        self,
        email: str,
    ) -> dict[str, Any]:
        """Get enriched contact information."""
        try:
            person = await self.enrich_person(email)
            if not person:
                return {}

            # Extract key fields with safe nested access
            organization = person.get("organization") or {}
            return {
                "first_name": person.get("first_name"),
                "last_name": person.get("last_name"),
                "email": person.get("email"),
                "phone": person.get("phone_number"),
                "linkedin_url": person.get("linkedin_url"),
                "title": person.get("title"),
                "company_name": organization.get("name") if organization else None,
                "company_domain": organization.get("primary_domain") if organization else None,
                "company_industry": organization.get("industry") if organization else None,
            }
        except Exception as e:
            logger.warning("contact_enrichment_failed", email=email, error=str(e))
            return {}

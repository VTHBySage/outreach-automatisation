"""HeyReach API client for LinkedIn automation and lead enrichment.

HeyReach provides:
1. LinkedIn campaign automation (connection requests, messages)
2. Lead enrichment from LinkedIn profiles
3. Profile lookup and search
4. Contact data extraction

This replaces LinkedIn Sales Navigator for data extraction needs.
"""

from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.core.exceptions import IntegrationError
from app.core.logging import get_logger
from app.integrations.base import BaseClient

logger = get_logger(__name__)


@dataclass
class LinkedInProfile:
    """Extracted LinkedIn profile data."""

    linkedin_url: str
    first_name: str | None
    last_name: str | None
    headline: str | None
    company_name: str | None
    company_linkedin_url: str | None
    job_title: str | None
    location: str | None
    industry: str | None
    connections_count: int | None
    profile_picture_url: str | None
    about: str | None
    email: str | None  # If available


@dataclass
class LinkedInCompany:
    """Extracted LinkedIn company data."""

    linkedin_url: str
    name: str
    industry: str | None
    company_size: str | None  # e.g., "51-200 employees"
    headquarters: str | None
    website: str | None
    description: str | None
    specialties: list[str]
    founded_year: int | None


class HeyReachError(IntegrationError):
    """HeyReach-specific integration error."""

    pass


class HeyReachClient(BaseClient):
    """Client for HeyReach LinkedIn automation API."""

    BASE_URL = "https://api.heyreach.io/api/v1"

    def __init__(self):
        api_key = getattr(settings, "heyreach_api_key", None)
        if api_key:
            api_key = api_key.get_secret_value() if hasattr(api_key, "get_secret_value") else api_key
        else:
            api_key = ""
            logger.warning("heyreach_api_key_not_configured")

        super().__init__(
            base_url=self.BASE_URL,
            api_key=api_key,
            integration_name="heyreach",
        )

    def _get_default_headers(self) -> dict[str, str]:
        """Get default headers with HeyReach auth."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["X-API-KEY"] = self.api_key
        return headers

    async def get_campaigns(self, status: str | None = None) -> list[dict[str, Any]]:
        """Get all LinkedIn campaigns."""
        try:
            params = {}
            if status:
                params["status"] = status
            response = await self.get("/campaigns", params=params)
            return response.get("data", [])
        except Exception as e:
            raise HeyReachError(f"Failed to get campaigns: {e}")

    async def get_campaign(self, campaign_id: str) -> dict[str, Any]:
        """Get campaign by ID."""
        try:
            return await self.get(f"/campaigns/{campaign_id}")
        except Exception as e:
            raise HeyReachError(f"Failed to get campaign {campaign_id}: {e}")

    async def add_lead_to_campaign(
        self,
        campaign_id: str,
        linkedin_url: str,
        first_name: str | None = None,
        last_name: str | None = None,
        company_name: str | None = None,
        email: str | None = None,
        custom_fields: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Add a lead to a LinkedIn campaign."""
        try:
            payload = {
                "linkedin_url": linkedin_url,
                "first_name": first_name,
                "last_name": last_name,
                "company_name": company_name,
                "email": email,
                **(custom_fields or {}),
            }
            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}

            return await self.post(
                f"/campaigns/{campaign_id}/leads",
                json=payload,
            )
        except Exception as e:
            raise HeyReachError(f"Failed to add lead to campaign {campaign_id}: {e}")

    async def remove_lead_from_campaign(
        self,
        campaign_id: str,
        lead_id: str,
    ) -> dict[str, Any]:
        """Remove a lead from a campaign."""
        try:
            return await self.delete(f"/campaigns/{campaign_id}/leads/{lead_id}")
        except Exception as e:
            raise HeyReachError(f"Failed to remove lead {lead_id} from campaign {campaign_id}: {e}")

    async def get_lead_by_linkedin_url(self, linkedin_url: str) -> dict[str, Any] | None:
        """Find a lead by LinkedIn URL."""
        try:
            response = await self.get(
                "/leads/search",
                params={"linkedin_url": linkedin_url},
            )
            leads = response.get("data", [])
            return leads[0] if leads else None
        except Exception as e:
            raise HeyReachError(f"Failed to find lead by LinkedIn URL: {e}")

    async def get_conversation_messages(
        self,
        conversation_id: str,
    ) -> list[dict[str, Any]]:
        """Get messages from a LinkedIn conversation."""
        try:
            response = await self.get(f"/conversations/{conversation_id}/messages")
            return response.get("data", [])
        except Exception as e:
            raise HeyReachError(f"Failed to get conversation messages: {e}")

    async def send_message(
        self,
        conversation_id: str,
        message: str,
    ) -> dict[str, Any]:
        """Send a message in a LinkedIn conversation."""
        try:
            return await self.post(
                f"/conversations/{conversation_id}/messages",
                json={"message": message},
            )
        except Exception as e:
            raise HeyReachError(f"Failed to send message: {e}")

    async def pause_lead_in_campaign(
        self,
        campaign_id: str,
        lead_id: str,
    ) -> dict[str, Any]:
        """Pause a lead in a campaign (stop sending messages)."""
        try:
            return await self.post(
                f"/campaigns/{campaign_id}/leads/{lead_id}/pause",
                json={},
            )
        except Exception as e:
            raise HeyReachError(f"Failed to pause lead {lead_id}: {e}")

    async def resume_lead_in_campaign(
        self,
        campaign_id: str,
        lead_id: str,
    ) -> dict[str, Any]:
        """Resume a paused lead in a campaign."""
        try:
            return await self.post(
                f"/campaigns/{campaign_id}/leads/{lead_id}/resume",
                json={},
            )
        except Exception as e:
            raise HeyReachError(f"Failed to resume lead {lead_id}: {e}")

    # =========================================================================
    # Lead Enrichment & Profile Lookup (Sales Navigator replacement)
    # =========================================================================

    async def enrich_profile(self, linkedin_url: str) -> LinkedInProfile | None:
        """
        Enrich a LinkedIn profile URL with full profile data.

        This replaces LinkedIn Sales Navigator profile lookup.

        Args:
            linkedin_url: LinkedIn profile URL

        Returns:
            LinkedInProfile with extracted data, or None if not found
        """
        try:
            response = await self.post(
                "/enrichment/profile",
                json={"linkedin_url": linkedin_url},
            )

            if not response or response.get("status") == "not_found":
                return None

            data = response.get("data", {})
            return LinkedInProfile(
                linkedin_url=linkedin_url,
                first_name=data.get("first_name"),
                last_name=data.get("last_name"),
                headline=data.get("headline"),
                company_name=data.get("company_name"),
                company_linkedin_url=data.get("company_linkedin_url"),
                job_title=data.get("job_title"),
                location=data.get("location"),
                industry=data.get("industry"),
                connections_count=data.get("connections_count"),
                profile_picture_url=data.get("profile_picture_url"),
                about=data.get("about"),
                email=data.get("email"),
            )
        except Exception as e:
            logger.warning(
                "profile_enrichment_failed",
                linkedin_url=linkedin_url,
                error=str(e),
            )
            return None

    async def enrich_company(self, linkedin_url: str) -> LinkedInCompany | None:
        """
        Enrich a LinkedIn company page with full company data.

        Args:
            linkedin_url: LinkedIn company page URL

        Returns:
            LinkedInCompany with extracted data, or None if not found
        """
        try:
            response = await self.post(
                "/enrichment/company",
                json={"linkedin_url": linkedin_url},
            )

            if not response or response.get("status") == "not_found":
                return None

            data = response.get("data", {})
            return LinkedInCompany(
                linkedin_url=linkedin_url,
                name=data.get("name", ""),
                industry=data.get("industry"),
                company_size=data.get("company_size"),
                headquarters=data.get("headquarters"),
                website=data.get("website"),
                description=data.get("description"),
                specialties=data.get("specialties", []),
                founded_year=data.get("founded_year"),
            )
        except Exception as e:
            logger.warning(
                "company_enrichment_failed",
                linkedin_url=linkedin_url,
                error=str(e),
            )
            return None

    async def search_people(
        self,
        keywords: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        company_name: str | None = None,
        job_title: str | None = None,
        location: str | None = None,
        industry: str | None = None,
        limit: int = 25,
    ) -> list[LinkedInProfile]:
        """
        Search for LinkedIn profiles matching criteria.

        This replaces LinkedIn Sales Navigator search.

        Args:
            keywords: General search keywords
            first_name: First name filter
            last_name: Last name filter
            company_name: Company name filter
            job_title: Job title filter
            location: Location filter
            industry: Industry filter
            limit: Max results to return

        Returns:
            List of matching LinkedInProfile objects
        """
        try:
            params = {
                "keywords": keywords,
                "first_name": first_name,
                "last_name": last_name,
                "company_name": company_name,
                "job_title": job_title,
                "location": location,
                "industry": industry,
                "limit": limit,
            }
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}

            response = await self.post("/search/people", json=params)

            profiles = []
            for data in response.get("data", []):
                profiles.append(
                    LinkedInProfile(
                        linkedin_url=data.get("linkedin_url", ""),
                        first_name=data.get("first_name"),
                        last_name=data.get("last_name"),
                        headline=data.get("headline"),
                        company_name=data.get("company_name"),
                        company_linkedin_url=data.get("company_linkedin_url"),
                        job_title=data.get("job_title"),
                        location=data.get("location"),
                        industry=data.get("industry"),
                        connections_count=data.get("connections_count"),
                        profile_picture_url=data.get("profile_picture_url"),
                        about=None,  # Not included in search results
                        email=data.get("email"),
                    )
                )
            return profiles

        except Exception as e:
            logger.warning("people_search_failed", error=str(e))
            return []

    async def search_companies(
        self,
        keywords: str | None = None,
        name: str | None = None,
        industry: str | None = None,
        company_size: str | None = None,
        location: str | None = None,
        limit: int = 25,
    ) -> list[LinkedInCompany]:
        """
        Search for LinkedIn company pages matching criteria.

        Args:
            keywords: General search keywords
            name: Company name filter
            industry: Industry filter
            company_size: Size filter (e.g., "51-200")
            location: Location filter
            limit: Max results to return

        Returns:
            List of matching LinkedInCompany objects
        """
        try:
            params = {
                "keywords": keywords,
                "name": name,
                "industry": industry,
                "company_size": company_size,
                "location": location,
                "limit": limit,
            }
            params = {k: v for k, v in params.items() if v is not None}

            response = await self.post("/search/companies", json=params)

            companies = []
            for data in response.get("data", []):
                companies.append(
                    LinkedInCompany(
                        linkedin_url=data.get("linkedin_url", ""),
                        name=data.get("name", ""),
                        industry=data.get("industry"),
                        company_size=data.get("company_size"),
                        headquarters=data.get("headquarters"),
                        website=data.get("website"),
                        description=data.get("description"),
                        specialties=data.get("specialties", []),
                        founded_year=data.get("founded_year"),
                    )
                )
            return companies

        except Exception as e:
            logger.warning("company_search_failed", error=str(e))
            return []

    async def find_profile_by_email(self, email: str) -> LinkedInProfile | None:
        """
        Find a LinkedIn profile by email address.

        This replaces Apollo/Sales Navigator email-to-LinkedIn lookup.

        Args:
            email: Email address to search

        Returns:
            LinkedInProfile if found, None otherwise
        """
        try:
            response = await self.post(
                "/enrichment/email-to-linkedin",
                json={"email": email},
            )

            if not response or response.get("status") == "not_found":
                return None

            data = response.get("data", {})
            linkedin_url = data.get("linkedin_url")

            if linkedin_url:
                # Get full profile enrichment
                return await self.enrich_profile(linkedin_url)

            return None

        except Exception as e:
            logger.warning(
                "email_to_linkedin_lookup_failed",
                email=email,
                error=str(e),
            )
            return None

    async def get_lead_enrichment_for_validation(
        self,
        linkedin_url: str | None = None,
        email: str | None = None,
        company_domain: str | None = None,
    ) -> dict[str, Any]:
        """
        Get enriched lead data for LLM company validation.

        Combines LinkedIn profile and company data for validation.
        This is the main method for the validation flow:
        Lead Source → LinkedIn Crawling → LLM Analysis → Classification

        Args:
            linkedin_url: LinkedIn profile URL
            email: Email address (for profile lookup)
            company_domain: Company domain (for company lookup)

        Returns:
            Dict with profile and company data for LLM validation
        """
        result = {
            "profile": None,
            "company": None,
            "linkedin_url": linkedin_url,
        }

        # Get profile by LinkedIn URL or email
        profile = None
        if linkedin_url:
            profile = await self.enrich_profile(linkedin_url)
        elif email:
            profile = await self.find_profile_by_email(email)

        if profile:
            result["profile"] = {
                "first_name": profile.first_name,
                "last_name": profile.last_name,
                "headline": profile.headline,
                "company_name": profile.company_name,
                "job_title": profile.job_title,
                "industry": profile.industry,
                "location": profile.location,
            }
            result["linkedin_url"] = profile.linkedin_url

            # Get company data if we have company LinkedIn URL
            if profile.company_linkedin_url:
                company = await self.enrich_company(profile.company_linkedin_url)
                if company:
                    result["company"] = {
                        "name": company.name,
                        "industry": company.industry,
                        "company_size": company.company_size,
                        "headquarters": company.headquarters,
                        "website": company.website,
                        "description": company.description,
                        "specialties": company.specialties,
                    }

        return result

    def to_llm_validation_context(self, enrichment_data: dict[str, Any]) -> str:
        """
        Convert enrichment data to context string for LLM validation.

        Args:
            enrichment_data: Result from get_lead_enrichment_for_validation

        Returns:
            Formatted string for LLM context
        """
        parts = []

        profile = enrichment_data.get("profile")
        if profile:
            parts.append("LinkedIn Profile Data:")
            if profile.get("first_name") or profile.get("last_name"):
                parts.append(f"  Name: {profile.get('first_name', '')} {profile.get('last_name', '')}".strip())
            if profile.get("headline"):
                parts.append(f"  Headline: {profile['headline']}")
            if profile.get("job_title"):
                parts.append(f"  Job Title: {profile['job_title']}")
            if profile.get("company_name"):
                parts.append(f"  Company: {profile['company_name']}")
            if profile.get("industry"):
                parts.append(f"  Industry: {profile['industry']}")
            if profile.get("location"):
                parts.append(f"  Location: {profile['location']}")

        company = enrichment_data.get("company")
        if company:
            parts.append("\nLinkedIn Company Data:")
            if company.get("name"):
                parts.append(f"  Company Name: {company['name']}")
            if company.get("industry"):
                parts.append(f"  Industry: {company['industry']}")
            if company.get("company_size"):
                parts.append(f"  Size: {company['company_size']}")
            if company.get("headquarters"):
                parts.append(f"  Headquarters: {company['headquarters']}")
            if company.get("website"):
                parts.append(f"  Website: {company['website']}")
            if company.get("description"):
                parts.append(f"  Description: {company['description'][:500]}...")
            if company.get("specialties"):
                parts.append(f"  Specialties: {', '.join(company['specialties'][:10])}")

        return "\n".join(parts) if parts else ""

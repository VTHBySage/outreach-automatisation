"""LLM-powered company validation service.

Validates if target companies match campaign criteria by:
1. Crawling company homepage
2. Enriching with Apollo data (optional)
3. Analyzing with OpenAI to classify company type
4. Returning match result with confidence score
"""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ValidationStatus
from app.core.exceptions import IntegrationError
from app.core.logging import get_logger
from app.db.models.campaign import Campaign
from app.db.models.contact import Contact
from app.integrations.apollo.client import ApolloClient
from app.integrations.openai.client import OpenAIClient
from app.integrations.webcrawler import WebCrawlerClient

logger = get_logger(__name__)


class ValidationError(IntegrationError):
    """Company validation specific error."""

    pass


@dataclass
class CompanyValidationResult:
    """Result of LLM company validation."""

    is_match: bool
    confidence: Decimal
    company_type: str
    reasoning: str
    needs_review: bool  # True if confidence is in review threshold range


# JSON Schema for OpenAI structured output
VALIDATION_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "company_validation",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "is_match": {
                    "type": "boolean",
                    "description": "True if company matches target criteria",
                },
                "confidence": {
                    "type": "number",
                    "description": "Confidence score from 0.0 to 1.0",
                },
                "company_type": {
                    "type": "string",
                    "description": "Detected company type (e.g., 'hotel_chain', 'vacation_rental', 'restaurant')",
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of the classification decision",
                },
            },
            "required": ["is_match", "confidence", "company_type", "reasoning"],
            "additionalProperties": False,
        },
    },
}

SYSTEM_PROMPT = """You are a B2B lead qualification expert. Your task is to analyze company information and determine if the company matches the target criteria for a marketing campaign.

You will receive:
1. Target criteria (what types of companies we're looking for)
2. Company information (from their website and/or enrichment data)

Your job is to:
1. Identify what type of business the company is
2. Determine if it matches the target criteria
3. Provide a confidence score (0.0 to 1.0)
4. Explain your reasoning briefly

Be conservative with matches - only mark as "is_match: true" if you're confident the company genuinely fits the target criteria. When in doubt, lean toward "is_match: false" with a note in the reasoning."""

USER_PROMPT_TEMPLATE = """## Campaign Target Criteria

**Target Company Types:** {target_types}
**Target Industries:** {target_industries}
**Exclude Types:** {exclude_types}
**Employee Size Range:** {employee_range}

---

## Company Information

**Company Name:** {company_name}
**Domain:** {company_domain}

### Website Content:
{website_content}

### Additional Data (if available):
{enrichment_data}

---

Analyze this company and determine if it matches the campaign's target criteria. Return your assessment as JSON."""


class CompanyValidationService:
    """Service for LLM-powered company validation against campaign criteria."""

    def __init__(
        self,
        session: AsyncSession,
        openai_client: OpenAIClient | None = None,
        webcrawler_client: WebCrawlerClient | None = None,
        apollo_client: ApolloClient | None = None,
    ):
        self.session = session
        self.openai_client = openai_client or OpenAIClient()
        self.webcrawler = webcrawler_client or WebCrawlerClient()
        self.apollo = apollo_client

    async def validate_company(
        self,
        company_name: str,
        company_domain: str | None,
        campaign: Campaign,
        use_enrichment: bool = True,
    ) -> CompanyValidationResult:
        """
        Validate if a company matches campaign targeting criteria.

        Args:
            company_name: Name of the company
            company_domain: Company website domain (optional but recommended)
            campaign: Campaign with target criteria
            use_enrichment: Whether to fetch additional data from Apollo

        Returns:
            CompanyValidationResult with match status, confidence, and reasoning

        Raises:
            ValidationError: If validation fails
        """
        logger.info(
            "validating_company",
            company_name=company_name,
            company_domain=company_domain,
            campaign_id=str(campaign.id),
        )

        try:
            # Step 1: Crawl website (homepage only for speed)
            website_content = "No website data available."
            if company_domain:
                try:
                    web_info = await self.webcrawler.fetch_homepage_only(company_domain)
                    website_content = self.webcrawler.to_llm_context(web_info)
                except Exception as e:
                    logger.warning(
                        "website_crawl_failed",
                        domain=company_domain,
                        error=str(e),
                    )

            # Step 2: Enrich with Apollo data (optional)
            enrichment_data = "No enrichment data available."
            if use_enrichment and self.apollo and company_domain:
                try:
                    apollo_data = await self.apollo.search_companies(
                        domains=[company_domain],
                        per_page=1,
                    )
                    if apollo_data.get("accounts"):
                        account = apollo_data["accounts"][0]
                        enrichment_data = self._format_apollo_data(account)
                except Exception as e:
                    logger.warning(
                        "apollo_enrichment_failed",
                        domain=company_domain,
                        error=str(e),
                    )

            # Step 3: Build LLM prompt
            criteria = campaign.get_criteria_dict()
            employee_range = "Any size"
            if criteria.get("min_employees") or criteria.get("max_employees"):
                min_emp = criteria.get("min_employees", "any")
                max_emp = criteria.get("max_employees", "any")
                employee_range = f"{min_emp} - {max_emp} employees"

            user_prompt = USER_PROMPT_TEMPLATE.format(
                target_types=", ".join(criteria.get("target_types", [])) or "Not specified",
                target_industries=", ".join(criteria.get("industries", [])) or "Not specified",
                exclude_types=", ".join(criteria.get("exclude_types", [])) or "None",
                employee_range=employee_range,
                company_name=company_name,
                company_domain=company_domain or "Not provided",
                website_content=website_content,
                enrichment_data=enrichment_data,
            )

            # Step 4: Call OpenAI for classification
            response = await self.openai_client.create_completion(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                response_format=VALIDATION_RESPONSE_FORMAT,
                temperature=0.1,  # Low for consistency
            )

            # Step 5: Parse and return result
            result = self._parse_response(response, campaign)

            logger.info(
                "company_validation_complete",
                company_name=company_name,
                is_match=result.is_match,
                confidence=float(result.confidence),
                company_type=result.company_type,
                needs_review=result.needs_review,
            )

            return result

        except Exception as e:
            logger.error(
                "company_validation_failed",
                company_name=company_name,
                error=str(e),
            )
            raise ValidationError(f"Failed to validate company {company_name}: {e}")

    async def validate_contact(
        self,
        contact_id: UUID,
        campaign_id: UUID,
    ) -> CompanyValidationResult:
        """
        Validate a contact's company against their campaign criteria.

        Updates the contact's validation_status and validation_confidence.

        Args:
            contact_id: UUID of the contact to validate
            campaign_id: UUID of the campaign with criteria

        Returns:
            CompanyValidationResult
        """
        # Fetch contact and campaign
        contact = await self.session.get(Contact, contact_id)
        campaign = await self.session.get(Campaign, campaign_id)

        if not contact:
            raise ValidationError(f"Contact {contact_id} not found")
        if not campaign:
            raise ValidationError(f"Campaign {campaign_id} not found")

        # Validate
        result = await self.validate_company(
            company_name=contact.company_name,
            company_domain=contact.company_domain,
            campaign=campaign,
        )

        # Update contact validation fields
        if result.is_match and not result.needs_review:
            contact.validation_status = ValidationStatus.VALIDATED.value
        elif result.needs_review:
            contact.validation_status = ValidationStatus.PENDING.value
        else:
            contact.validation_status = ValidationStatus.REJECTED.value

        contact.validation_confidence = result.confidence
        contact.company_type = result.company_type
        contact.validation_notes = result.reasoning

        await self.session.flush()

        return result

    async def batch_validate_contacts(
        self,
        campaign_id: UUID,
        limit: int = 50,
    ) -> dict[str, int]:
        """
        Validate all pending contacts in a campaign.

        Args:
            campaign_id: UUID of the campaign
            limit: Maximum contacts to process in one batch

        Returns:
            Dict with counts: {'validated': N, 'rejected': M, 'review': R, 'errors': E}
        """
        campaign = await self.session.get(Campaign, campaign_id)
        if not campaign:
            raise ValidationError(f"Campaign {campaign_id} not found")

        # Get pending contacts for this campaign
        stmt = (
            select(Contact)
            .where(
                Contact.campaign_id == campaign_id,
                Contact.validation_status == ValidationStatus.PENDING.value,
                Contact.deleted_at.is_(None),
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        contacts = result.scalars().all()

        results = {"validated": 0, "rejected": 0, "review": 0, "errors": 0}

        for contact in contacts:
            try:
                validation = await self.validate_contact(contact.id, campaign_id)
                if validation.is_match and not validation.needs_review:
                    results["validated"] += 1
                elif validation.needs_review:
                    results["review"] += 1
                else:
                    results["rejected"] += 1
            except Exception as e:
                logger.error(
                    "batch_validation_error",
                    contact_id=str(contact.id),
                    error=str(e),
                )
                results["errors"] += 1

        await self.session.commit()

        logger.info(
            "batch_validation_complete",
            campaign_id=str(campaign_id),
            **results,
        )

        return results

    def _parse_response(
        self,
        response: dict,
        campaign: Campaign,
    ) -> CompanyValidationResult:
        """Parse OpenAI response into CompanyValidationResult."""
        confidence = Decimal(str(response["confidence"]))

        # Determine if needs manual review (between review_threshold and min_confidence)
        needs_review = (
            confidence >= campaign.review_threshold
            and confidence < campaign.min_confidence
        )

        # Match requires confidence >= min_confidence (unless in review range)
        is_match = response["is_match"] and confidence >= campaign.review_threshold

        return CompanyValidationResult(
            is_match=is_match and confidence >= campaign.min_confidence,
            confidence=confidence,
            company_type=response["company_type"],
            reasoning=response["reasoning"],
            needs_review=needs_review,
        )

    def _format_apollo_data(self, account: dict) -> str:
        """Format Apollo account data for LLM context."""
        parts = []

        if account.get("name"):
            parts.append(f"Company Name (Apollo): {account['name']}")
        if account.get("industry"):
            parts.append(f"Industry: {account['industry']}")
        if account.get("estimated_num_employees"):
            parts.append(f"Employees: {account['estimated_num_employees']}")
        if account.get("short_description"):
            parts.append(f"Description: {account['short_description']}")
        if account.get("keywords"):
            parts.append(f"Keywords: {', '.join(account['keywords'][:10])}")
        if account.get("founded_year"):
            parts.append(f"Founded: {account['founded_year']}")
        if account.get("annual_revenue"):
            parts.append(f"Annual Revenue: {account['annual_revenue']}")

        return "\n".join(parts) if parts else "No Apollo data available."

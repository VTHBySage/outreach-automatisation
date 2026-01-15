"""AI response categorization service."""

from dataclasses import dataclass
from decimal import Decimal

from app.core.constants import MainCategory, SubCategory
from app.core.exceptions import CategorizationError
from app.core.logging import get_logger
from app.integrations.openai.client import OpenAIClient
from app.services.categorization.prompts import (
    RESPONSE_FORMAT,
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
)

logger = get_logger(__name__)


@dataclass
class ReferralInfo:
    """Extracted referral contact information."""

    name: str | None
    email: str | None
    company: str | None


@dataclass
class CategorizationResult:
    """Result of AI categorization."""

    main_category: MainCategory
    subcategory: SubCategory
    confidence: Decimal
    reasoning: str
    suggested_followup_date: str | None = None  # ISO date for WRONG_TIMING
    referral_info: ReferralInfo | None = None  # For REFERRAL category


class CategorizationService:
    """Service for AI-powered response categorization."""

    def __init__(self, openai_client: OpenAIClient | None = None):
        self.openai_client = openai_client or OpenAIClient()

    async def categorize_reply(
        self,
        subject: str,
        body: str,
        context: str | None = None,
    ) -> CategorizationResult:
        """
        Categorize an email reply using AI.

        Args:
            subject: Email subject line
            body: Email body text
            context: Previous email thread context (optional)

        Returns:
            CategorizationResult with category, subcategory, confidence, and reasoning

        Raises:
            CategorizationError: If categorization fails
        """
        try:
            # Prepare prompt
            user_prompt = USER_PROMPT_TEMPLATE.format(
                subject=subject or "(no subject)",
                body=body,
                context=context or "(no previous context)",
            )

            # Call OpenAI
            response = await self.openai_client.create_completion(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                response_format=RESPONSE_FORMAT,
            )

            # Parse response
            result = self._parse_response(response)

            logger.info(
                "categorization_complete",
                main_category=result.main_category.value,
                subcategory=result.subcategory.value,
                confidence=float(result.confidence),
            )

            return result

        except Exception as e:
            logger.error("categorization_failed", error=str(e))
            raise CategorizationError(f"Failed to categorize reply: {e}")

    def _parse_response(self, response: dict) -> CategorizationResult:
        """Parse OpenAI response into CategorizationResult."""
        try:
            main_category = MainCategory(response["main_category"])
            subcategory = SubCategory(response["subcategory"])
            confidence = Decimal(str(response["confidence"]))
            reasoning = response["reasoning"]

            # Parse optional fields
            suggested_followup_date = response.get("suggested_followup_date")
            referral_info = None
            if response.get("referral_info"):
                referral_data = response["referral_info"]
                referral_info = ReferralInfo(
                    name=referral_data.get("name"),
                    email=referral_data.get("email"),
                    company=referral_data.get("company"),
                )

            return CategorizationResult(
                main_category=main_category,
                subcategory=subcategory,
                confidence=confidence,
                reasoning=reasoning,
                suggested_followup_date=suggested_followup_date,
                referral_info=referral_info,
            )
        except (KeyError, ValueError) as e:
            raise CategorizationError(f"Invalid categorization response: {e}")

    async def validate_company(
        self,
        company_name: str,
        company_domain: str | None,
        company_description: str | None,
        campaign_criteria: dict,
        use_web_crawl: bool = True,
        linkedin_url: str | None = None,
        contact_email: str | None = None,
    ) -> "CompanyValidationResult":
        """
        Validate if a company matches campaign criteria using AI.

        Implements the validation flow from Requirements.md:
        Lead Source → Website/LinkedIn Crawling → LLM Analysis → Classification

        Args:
            company_name: Name of the company
            company_domain: Company website domain
            company_description: Description from Apollo enrichment
            campaign_criteria: Dict with target_types, industries, exclude_types, etc.
            use_web_crawl: Whether to crawl company website for additional context
            linkedin_url: LinkedIn profile/company URL for enrichment
            contact_email: Contact email for LinkedIn lookup via HeyReach

        Returns:
            CompanyValidationResult with status, confidence, and reasoning
        """
        try:
            target_types = campaign_criteria.get("target_types", [])
            target_industries = campaign_criteria.get("industries", [])
            exclude_types = campaign_criteria.get("exclude_types", [])
            min_employees = campaign_criteria.get("min_employees")
            max_employees = campaign_criteria.get("max_employees")

            # Try to enrich with web crawl data
            web_context = ""
            if use_web_crawl and company_domain:
                try:
                    from app.integrations.webcrawler import WebCrawlerClient

                    crawler = WebCrawlerClient()
                    try:
                        web_info = await crawler.get_company_info(company_domain)
                        web_context = crawler.to_llm_context(web_info)
                    finally:
                        await crawler.close()
                except Exception as e:
                    logger.warning(
                        "web_crawl_failed",
                        company_name=company_name,
                        domain=company_domain,
                        error=str(e),
                    )
                    web_context = ""

            # Try to enrich with LinkedIn data via HeyReach (replaces Sales Navigator)
            linkedin_context = ""
            if linkedin_url or contact_email:
                try:
                    from app.integrations.heyreach import HeyReachClient

                    heyreach = HeyReachClient()
                    try:
                        enrichment = await heyreach.get_lead_enrichment_for_validation(
                            linkedin_url=linkedin_url,
                            email=contact_email,
                            company_domain=company_domain,
                        )
                        linkedin_context = heyreach.to_llm_validation_context(enrichment)
                    finally:
                        await heyreach.close()
                except Exception as e:
                    logger.warning(
                        "linkedin_enrichment_failed",
                        company_name=company_name,
                        linkedin_url=linkedin_url,
                        error=str(e),
                    )
                    linkedin_context = ""

            system_prompt = """You are a B2B lead qualification expert. Your task is to evaluate if a company matches campaign targeting criteria.

Analyze all provided company information (Apollo data, website data, LinkedIn data) and campaign criteria, then provide a validation decision with confidence score.

You MUST respond in JSON format with these exact fields:
- is_match: boolean (true if company matches criteria, false otherwise)
- confidence: number between 0.0 and 1.0
- company_type: string (your best classification of the company type)
- reasoning: string (brief explanation of your decision)
- needs_review: boolean (true if confidence is between 0.75-0.85 and needs manual review)"""

            user_prompt = f"""Company Information:
- Name: {company_name}
- Domain: {company_domain or 'Unknown'}
- Description: {company_description or 'No description available'}

{f'Website Data:{chr(10)}{web_context}' if web_context else ''}

{f'LinkedIn Data:{chr(10)}{linkedin_context}' if linkedin_context else ''}

Campaign Criteria:
- Target Company Types: {', '.join(target_types) if target_types else 'Any'}
- Target Industries: {', '.join(target_industries) if target_industries else 'Any'}
- Excluded Types: {', '.join(exclude_types) if exclude_types else 'None'}
- Employee Range: {f'{min_employees}-{max_employees}' if min_employees or max_employees else 'Any size'}

Evaluate if this company is a good match for the campaign based on ALL available data sources."""

            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "company_validation",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "is_match": {"type": "boolean"},
                            "confidence": {"type": "number"},
                            "company_type": {"type": "string"},
                            "reasoning": {"type": "string"},
                            "needs_review": {"type": "boolean"},
                        },
                        "required": ["is_match", "confidence", "company_type", "reasoning", "needs_review"],
                    },
                },
            }

            response = await self.openai_client.create_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format=response_format,
            )

            result = CompanyValidationResult(
                is_match=response["is_match"],
                confidence=Decimal(str(response["confidence"])),
                company_type=response["company_type"],
                reasoning=response["reasoning"],
                needs_review=response["needs_review"],
            )

            logger.info(
                "company_validation_complete",
                company_name=company_name,
                is_match=result.is_match,
                confidence=float(result.confidence),
                needs_review=result.needs_review,
            )

            return result

        except Exception as e:
            logger.error("company_validation_failed", company_name=company_name, error=str(e))
            raise CategorizationError(f"Failed to validate company: {e}")


@dataclass
class CompanyValidationResult:
    """Result of company validation."""

    is_match: bool
    confidence: Decimal
    company_type: str
    reasoning: str
    needs_review: bool

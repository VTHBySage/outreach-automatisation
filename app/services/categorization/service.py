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
class CategorizationResult:
    """Result of AI categorization."""

    main_category: MainCategory
    subcategory: SubCategory
    confidence: Decimal
    reasoning: str


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

            return CategorizationResult(
                main_category=main_category,
                subcategory=subcategory,
                confidence=confidence,
                reasoning=reasoning,
            )
        except (KeyError, ValueError) as e:
            raise CategorizationError(f"Invalid categorization response: {e}")

    async def validate_company(
        self,
        company_name: str,
        company_domain: str | None,
        company_description: str | None,
        campaign_criteria: dict,
    ) -> "CompanyValidationResult":
        """
        Validate if a company matches campaign criteria using AI.

        Args:
            company_name: Name of the company
            company_domain: Company website domain
            company_description: Description from Apollo enrichment
            campaign_criteria: Dict with target_types, industries, exclude_types, etc.

        Returns:
            CompanyValidationResult with status, confidence, and reasoning
        """
        try:
            target_types = campaign_criteria.get("target_types", [])
            target_industries = campaign_criteria.get("industries", [])
            exclude_types = campaign_criteria.get("exclude_types", [])
            min_employees = campaign_criteria.get("min_employees")
            max_employees = campaign_criteria.get("max_employees")

            system_prompt = """You are a B2B lead qualification expert. Your task is to evaluate if a company matches campaign targeting criteria.

Analyze the company information and campaign criteria, then provide a validation decision with confidence score.

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

Campaign Criteria:
- Target Company Types: {', '.join(target_types) if target_types else 'Any'}
- Target Industries: {', '.join(target_industries) if target_industries else 'Any'}
- Excluded Types: {', '.join(exclude_types) if exclude_types else 'None'}
- Employee Range: {f'{min_employees}-{max_employees}' if min_employees or max_employees else 'Any size'}

Evaluate if this company is a good match for the campaign."""

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

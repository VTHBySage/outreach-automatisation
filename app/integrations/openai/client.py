"""OpenAI API client for categorization."""

import json
from typing import Any

from openai import AsyncOpenAI

from app.config import settings
from app.core.exceptions import OpenAIError
from app.core.logging import get_logger

logger = get_logger(__name__)


class OpenAIClient:
    """Client for OpenAI API."""

    def __init__(self, timeout: float = 60.0):
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            timeout=timeout,
        )
        self.model = settings.openai_model
        self.max_tokens = settings.openai_max_tokens

    async def create_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: dict[str, Any] | None = None,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        """
        Create a chat completion with structured output.

        Args:
            system_prompt: System message content
            user_prompt: User message content
            response_format: JSON schema for structured output
            temperature: Sampling temperature (lower = more deterministic)

        Returns:
            Parsed JSON response

        Raises:
            OpenAIError: If API call fails
        """
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": temperature,
            }

            if response_format:
                kwargs["response_format"] = response_format

            response = await self.client.chat.completions.create(**kwargs)

            # Validate response has choices
            if not response.choices:
                raise OpenAIError("No choices in response from OpenAI")

            # Extract content
            content = response.choices[0].message.content
            if not content:
                raise OpenAIError("Empty response from OpenAI")

            # Parse JSON
            try:
                result = json.loads(content)
            except json.JSONDecodeError as e:
                raise OpenAIError(f"Invalid JSON response: {e}")

            logger.info(
                "openai_completion",
                model=self.model,
                prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                completion_tokens=response.usage.completion_tokens if response.usage else 0,
            )

            return result

        except OpenAIError:
            raise
        except Exception as e:
            logger.error("openai_error", error=str(e))
            raise OpenAIError(f"OpenAI API error: {e}")

    async def generate_draft_message(
        self,
        context: str,
        category: str,
        lead_name: str,
    ) -> str | None:
        """
        Generate a draft response message.

        Returns:
            str: Generated message content
            None: If generation fails

        Raises:
            OpenAIError: If API call fails and caller should handle it
        """
        try:
            system_prompt = """You are a B2B sales professional. Generate a brief,
            professional response message based on the email context and categorization.
            Keep responses concise (2-3 sentences max) and action-oriented."""

            user_prompt = f"""Generate a draft response for this lead:

Lead Name: {lead_name}
Category: {category}
Context: {context}

Write a professional response appropriate for this category."""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=200,
                temperature=0.7,
            )

            # Validate response has choices
            if not response.choices:
                logger.error(
                    "draft_generation_no_choices",
                    lead_name=lead_name,
                    category=category,
                )
                return None

            content = response.choices[0].message.content
            if not content:
                logger.warning(
                    "draft_generation_empty_content",
                    lead_name=lead_name,
                    category=category,
                )
                return None

            return content

        except Exception as e:
            logger.error(
                "draft_generation_failed",
                lead_name=lead_name,
                category=category,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

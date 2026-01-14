"""Base HTTP client with retry logic and rate limiting."""

import asyncio
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.exceptions import IntegrationError, RateLimitError
from app.core.logging import get_logger

logger = get_logger(__name__)


class BaseClient:
    """Base HTTP client with retry and error handling."""

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self._get_default_headers(),
            )
        return self._client

    def _get_default_headers(self) -> dict[str, str]:
        """Get default headers for requests."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        _retry_count: int = 0,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Make HTTP request with retry logic and rate limit handling.

        Handles 429 Too Many Requests by:
        1. Reading Retry-After header if present
        2. Using exponential backoff if no header
        3. Retrying up to max_retries times
        """
        client = await self._get_client()

        try:
            response = await client.request(method, path, **kwargs)

            # Handle rate limiting (429)
            if response.status_code == 429:
                retry_after = self._parse_retry_after(response)
                if _retry_count < self.max_retries:
                    wait_time = retry_after or (2 ** _retry_count)  # Exponential backoff fallback
                    logger.warning(
                        "rate_limit_hit_retrying",
                        method=method,
                        path=path,
                        retry_after=wait_time,
                        retry_count=_retry_count + 1,
                    )
                    await asyncio.sleep(wait_time)
                    return await self._request(method, path, _retry_count=_retry_count + 1, **kwargs)
                else:
                    raise RateLimitError(
                        f"Rate limit exceeded after {self.max_retries} retries",
                        retry_after=retry_after,
                    )

            response.raise_for_status()

            # Handle 204 No Content and empty responses
            if response.status_code == 204 or not response.content:
                return {}

            return response.json()

        except httpx.HTTPStatusError as e:
            # Retry on 5xx errors
            if e.response.status_code >= 500 and _retry_count < self.max_retries:
                wait_time = 2 ** _retry_count
                logger.warning(
                    "server_error_retrying",
                    method=method,
                    path=path,
                    status_code=e.response.status_code,
                    retry_count=_retry_count + 1,
                )
                await asyncio.sleep(wait_time)
                return await self._request(method, path, _retry_count=_retry_count + 1, **kwargs)

            logger.error(
                "http_error",
                method=method,
                path=path,
                status_code=e.response.status_code,
                response_text=e.response.text[:500],
            )
            raise IntegrationError(
                f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            )

        except httpx.TimeoutException as e:
            # Retry on timeout
            if _retry_count < self.max_retries:
                wait_time = 2 ** _retry_count
                logger.warning(
                    "timeout_retrying",
                    method=method,
                    path=path,
                    retry_count=_retry_count + 1,
                )
                await asyncio.sleep(wait_time)
                return await self._request(method, path, _retry_count=_retry_count + 1, **kwargs)

            logger.error(
                "timeout_error",
                method=method,
                path=path,
                error=str(e),
            )
            raise IntegrationError(f"Request timed out: {e}")

        except httpx.ConnectError as e:
            logger.error(
                "connection_error",
                method=method,
                path=path,
                error=str(e),
            )
            raise IntegrationError(f"Connection failed: {e}")

        except httpx.RequestError as e:
            logger.error(
                "request_error",
                method=method,
                path=path,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise IntegrationError(f"Request failed: {e}")

    def _parse_retry_after(self, response: httpx.Response) -> int | None:
        """Parse Retry-After header from response."""
        retry_after = response.headers.get("Retry-After")
        if not retry_after:
            return None
        try:
            return int(retry_after)
        except ValueError:
            # Could be a date string, default to 60 seconds
            return 60

    async def get(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """Make GET request."""
        return await self._request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """Make POST request."""
        return await self._request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """Make PUT request."""
        return await self._request("PUT", path, **kwargs)

    async def patch(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """Make PATCH request."""
        return await self._request("PATCH", path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """Make DELETE request."""
        return await self._request("DELETE", path, **kwargs)

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

"""Web crawler for extracting company information from websites."""

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.core.exceptions import IntegrationError
from app.core.logging import get_logger

logger = get_logger(__name__)


class WebCrawlerError(IntegrationError):
    """Web crawler specific error."""

    pass


@dataclass
class CompanyWebInfo:
    """Extracted company information from website."""

    domain: str
    title: str | None
    description: str | None
    about_text: str | None
    services: list[str]
    industries: list[str]
    meta_keywords: list[str]
    social_links: dict[str, str]
    contact_info: dict[str, str]


class WebCrawlerClient:
    """Client for crawling company websites to extract validation data."""

    # Common about page paths to try
    ABOUT_PATHS = [
        "/about",
        "/about-us",
        "/company",
        "/who-we-are",
        "/our-story",
        "/about.html",
    ]

    # Common services page paths
    SERVICES_PATHS = [
        "/services",
        "/solutions",
        "/products",
        "/what-we-do",
    ]

    def __init__(
        self,
        timeout: float = 15.0,
        max_content_length: int = 1_000_000,  # 1MB limit
    ):
        self.timeout = timeout
        self.max_content_length = max_content_length
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; OutreachBot/1.0; Company Validation)",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                },
            )
        return self._client

    async def fetch_page(self, url: str) -> str | None:
        """Fetch a page and return HTML content."""
        try:
            client = await self._get_client()
            response = await client.get(url)

            if response.status_code != 200:
                return None

            # Check content length
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > self.max_content_length:
                logger.warning(
                    "page_too_large",
                    url=url,
                    content_length=content_length,
                )
                return None

            return response.text

        except httpx.TimeoutException:
            logger.warning("page_fetch_timeout", url=url)
            return None
        except httpx.RequestError as e:
            logger.warning("page_fetch_error", url=url, error=str(e))
            return None

    def _extract_text(self, soup: BeautifulSoup, max_length: int = 5000) -> str:
        """Extract clean text from HTML, limiting length."""
        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            element.decompose()

        text = soup.get_text(separator=" ", strip=True)
        # Clean up whitespace
        text = re.sub(r"\s+", " ", text)
        return text[:max_length]

    def _extract_meta(self, soup: BeautifulSoup) -> dict[str, str | None]:
        """Extract meta tags from HTML."""
        meta = {
            "title": None,
            "description": None,
            "keywords": None,
        }

        # Title
        title_tag = soup.find("title")
        if title_tag:
            meta["title"] = title_tag.get_text(strip=True)

        # Meta description
        desc_tag = soup.find("meta", attrs={"name": "description"})
        if desc_tag:
            meta["description"] = desc_tag.get("content")

        # OG description fallback
        if not meta["description"]:
            og_desc = soup.find("meta", attrs={"property": "og:description"})
            if og_desc:
                meta["description"] = og_desc.get("content")

        # Meta keywords
        keywords_tag = soup.find("meta", attrs={"name": "keywords"})
        if keywords_tag:
            meta["keywords"] = keywords_tag.get("content")

        return meta

    def _extract_social_links(self, soup: BeautifulSoup, base_url: str) -> dict[str, str]:
        """Extract social media links from HTML."""
        social_links = {}
        social_patterns = {
            "linkedin": r"linkedin\.com",
            "twitter": r"(twitter\.com|x\.com)",
            "facebook": r"facebook\.com",
            "instagram": r"instagram\.com",
            "youtube": r"youtube\.com",
        }

        for link in soup.find_all("a", href=True):
            href = link["href"]
            for platform, pattern in social_patterns.items():
                if re.search(pattern, href, re.IGNORECASE):
                    social_links[platform] = href
                    break

        return social_links

    def _extract_contact_info(self, text: str) -> dict[str, str]:
        """Extract contact information from text."""
        contact_info = {}

        # Email pattern
        email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
        if email_match:
            contact_info["email"] = email_match.group()

        # Phone pattern (various formats)
        phone_match = re.search(
            r"(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}",
            text,
        )
        if phone_match:
            contact_info["phone"] = phone_match.group()

        return contact_info

    def _extract_services(self, soup: BeautifulSoup) -> list[str]:
        """Extract service/product keywords from page."""
        services = set()

        # Look for service keywords in headings
        for heading in soup.find_all(["h1", "h2", "h3", "h4"]):
            text = heading.get_text(strip=True).lower()
            if any(word in text for word in ["service", "solution", "product", "offer"]):
                services.add(heading.get_text(strip=True))

        # Look in lists
        for ul in soup.find_all("ul"):
            parent = ul.find_parent(["section", "div"])
            if parent:
                parent_text = parent.get_text(strip=True).lower()
                if any(word in parent_text for word in ["service", "solution", "offer"]):
                    for li in ul.find_all("li", limit=10):
                        services.add(li.get_text(strip=True)[:100])

        return list(services)[:20]  # Limit to 20 services

    async def fetch_homepage_only(self, domain: str) -> CompanyWebInfo:
        """
        Fetch only the homepage for fast validation (no additional pages).

        This is the optimized method for LLM company validation when speed
        is prioritized over comprehensive data collection.

        Args:
            domain: Company domain (e.g., "example.com")

        Returns:
            CompanyWebInfo with homepage-only data
        """
        # Normalize domain
        if not domain.startswith("http"):
            base_url = f"https://{domain}"
        else:
            base_url = domain
            domain = urlparse(base_url).netloc

        logger.info("crawling_homepage_only", domain=domain)

        result = CompanyWebInfo(
            domain=domain,
            title=None,
            description=None,
            about_text=None,
            services=[],
            industries=[],
            meta_keywords=[],
            social_links={},
            contact_info={},
        )

        try:
            homepage_html = await self.fetch_page(base_url)
            if homepage_html:
                soup = BeautifulSoup(homepage_html, "html.parser")

                # Extract meta info
                meta = self._extract_meta(soup)
                result.title = meta["title"]
                result.description = meta["description"]
                if meta["keywords"]:
                    result.meta_keywords = [
                        k.strip() for k in meta["keywords"].split(",")
                    ]

                # Extract social links
                result.social_links = self._extract_social_links(soup, base_url)

                # Extract contact info and services from homepage only
                homepage_text = self._extract_text(soup)
                result.contact_info = self._extract_contact_info(homepage_text)
                result.services = self._extract_services(soup)

                # Use homepage text as about_text substitute
                result.about_text = homepage_text[:2000]

            logger.info(
                "homepage_crawl_complete",
                domain=domain,
                has_title=result.title is not None,
                has_description=result.description is not None,
            )

            return result

        except Exception as e:
            logger.error("homepage_crawl_failed", domain=domain, error=str(e))
            raise WebCrawlerError(f"Failed to crawl homepage for {domain}: {e}")

    async def get_company_info(self, domain: str) -> CompanyWebInfo:
        """
        Crawl company website and extract validation information.

        Args:
            domain: Company domain (e.g., "example.com")

        Returns:
            CompanyWebInfo with extracted data
        """
        # Normalize domain
        if not domain.startswith("http"):
            base_url = f"https://{domain}"
        else:
            base_url = domain
            domain = urlparse(base_url).netloc

        logger.info("crawling_company_website", domain=domain)

        # Initialize result
        result = CompanyWebInfo(
            domain=domain,
            title=None,
            description=None,
            about_text=None,
            services=[],
            industries=[],
            meta_keywords=[],
            social_links={},
            contact_info={},
        )

        try:
            # Fetch homepage
            homepage_html = await self.fetch_page(base_url)
            if homepage_html:
                soup = BeautifulSoup(homepage_html, "html.parser")

                # Extract meta info
                meta = self._extract_meta(soup)
                result.title = meta["title"]
                result.description = meta["description"]
                if meta["keywords"]:
                    result.meta_keywords = [
                        k.strip() for k in meta["keywords"].split(",")
                    ]

                # Extract social links
                result.social_links = self._extract_social_links(soup, base_url)

                # Extract contact info
                homepage_text = self._extract_text(soup)
                result.contact_info = self._extract_contact_info(homepage_text)

                # Extract services from homepage
                result.services = self._extract_services(soup)

            # Try to fetch about page
            for about_path in self.ABOUT_PATHS:
                about_url = urljoin(base_url, about_path)
                about_html = await self.fetch_page(about_url)
                if about_html:
                    soup = BeautifulSoup(about_html, "html.parser")
                    result.about_text = self._extract_text(soup, max_length=3000)
                    break  # Found about page, stop trying

            # Try to fetch services page for more service info
            for services_path in self.SERVICES_PATHS:
                services_url = urljoin(base_url, services_path)
                services_html = await self.fetch_page(services_url)
                if services_html:
                    soup = BeautifulSoup(services_html, "html.parser")
                    services_text = self._extract_text(soup)
                    additional_services = self._extract_services(soup)
                    result.services.extend(additional_services)
                    result.services = list(set(result.services))[:20]
                    break

            logger.info(
                "company_crawl_complete",
                domain=domain,
                has_title=result.title is not None,
                has_description=result.description is not None,
                has_about=result.about_text is not None,
                services_count=len(result.services),
            )

            return result

        except Exception as e:
            logger.error(
                "company_crawl_failed",
                domain=domain,
                error=str(e),
            )
            raise WebCrawlerError(f"Failed to crawl {domain}: {e}")

    def to_llm_context(self, info: CompanyWebInfo) -> str:
        """
        Convert extracted info to context string for LLM validation.

        Args:
            info: Extracted company web info

        Returns:
            Formatted string for LLM context
        """
        parts = [f"Website Domain: {info.domain}"]

        if info.title:
            parts.append(f"Website Title: {info.title}")

        if info.description:
            parts.append(f"Meta Description: {info.description}")

        if info.about_text:
            parts.append(f"About Page Content: {info.about_text[:1500]}...")

        if info.services:
            parts.append(f"Services/Products: {', '.join(info.services[:10])}")

        if info.meta_keywords:
            parts.append(f"Keywords: {', '.join(info.meta_keywords[:10])}")

        if info.social_links:
            linkedin = info.social_links.get("linkedin")
            if linkedin:
                parts.append(f"LinkedIn: {linkedin}")

        return "\n".join(parts)

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

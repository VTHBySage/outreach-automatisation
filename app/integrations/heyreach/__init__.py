"""HeyReach LinkedIn automation and enrichment integration.

HeyReach serves as the LinkedIn data source, replacing LinkedIn Sales Navigator:
- Profile enrichment and lookup
- Company data extraction
- Email-to-LinkedIn matching
- Campaign automation
"""

from app.integrations.heyreach.client import (
    HeyReachClient,
    HeyReachError,
    LinkedInCompany,
    LinkedInProfile,
)

__all__ = [
    "HeyReachClient",
    "HeyReachError",
    "LinkedInProfile",
    "LinkedInCompany",
]

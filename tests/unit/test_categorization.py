"""Unit tests for categorization service."""

import pytest

from app.core.constants import MainCategory, SubCategory, SUBCATEGORY_TO_MAIN
from app.services.categorization.categories import CATEGORY_INFO


class TestCategoryConstants:
    """Tests for category constants."""

    def test_all_subcategories_have_main_category(self):
        """All subcategories should map to a main category."""
        for subcategory in SubCategory:
            assert subcategory in SUBCATEGORY_TO_MAIN, f"{subcategory} missing from SUBCATEGORY_TO_MAIN"

    def test_all_subcategories_have_info(self):
        """All subcategories should have info defined."""
        for subcategory in SubCategory:
            assert subcategory in CATEGORY_INFO, f"{subcategory} missing from CATEGORY_INFO"

    def test_subcategory_info_main_category_matches(self):
        """Category info main_category should match the mapping."""
        for subcategory, info in CATEGORY_INFO.items():
            expected = SUBCATEGORY_TO_MAIN[subcategory]
            assert info.main_category == expected, f"{subcategory} main_category mismatch"

    def test_main_category_count(self):
        """Should have exactly 5 main categories."""
        assert len(MainCategory) == 5

    def test_subcategory_count(self):
        """Should have exactly 26 subcategories."""
        assert len(SubCategory) == 26


class TestCategorizationService:
    """Tests for CategorizationService."""

    @pytest.mark.asyncio
    async def test_categorize_reply_placeholder(self):
        """Placeholder test for categorization service."""
        # TODO: Implement with mocked OpenAI client
        pass

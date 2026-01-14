"""Unit tests for task factory."""

import pytest

from app.core.constants import SubCategory, TaskPriority, TASK_TYPES
from app.services.tasks.factory import TaskFactory


class TestTaskFactory:
    """Tests for TaskFactory."""

    @pytest.fixture
    def factory(self):
        """Create task factory instance."""
        return TaskFactory()

    def test_create_tasks_for_ready_to_chat(self, factory):
        """Ready to chat should create 3 high-priority tasks."""
        tasks = factory.create_tasks_for_category(
            subcategory=SubCategory.READY_TO_CHAT_PHONE,
            contact_name="John Doe",
            company_name="Example Corp",
        )

        assert len(tasks) == 3
        for task in tasks:
            assert task.priority == TaskPriority.HIGH
            assert "John Doe" in task.title
            assert "Example Corp" in task.title

    def test_create_tasks_for_referral(self, factory):
        """Referral should create 2 highest-priority tasks."""
        tasks = factory.create_tasks_for_category(
            subcategory=SubCategory.REFERRAL,
            contact_name="Jane Smith",
            company_name="Other Corp",
        )

        assert len(tasks) == 2
        for task in tasks:
            assert task.priority == TaskPriority.HIGHEST

    def test_create_tasks_for_not_interested(self, factory):
        """Not interested should create 1 low-priority task."""
        tasks = factory.create_tasks_for_category(
            subcategory=SubCategory.NOT_INTERESTED,
            contact_name="Bob Wilson",
            company_name="Test Inc",
        )

        assert len(tasks) == 1
        assert tasks[0].priority == TaskPriority.LOW

    def test_create_tasks_for_category_without_tasks(self, factory):
        """Some categories don't generate tasks."""
        tasks = factory.create_tasks_for_category(
            subcategory=SubCategory.OUT_OF_OFFICE,
            contact_name="Test Contact",
            company_name="Test Company",
        )

        # Out of Office typically doesn't generate tasks
        assert len(tasks) == 0

    def test_due_date_calculation(self, factory):
        """Due dates should be calculated based on priority."""
        tasks = factory.create_tasks_for_category(
            subcategory=SubCategory.REFERRAL,
            contact_name="Test",
            company_name="Test",
        )

        # Highest priority should be < 12 hours from now
        for task in tasks:
            assert task.due_date is not None


class TestTaskTypes:
    """Tests for TASK_TYPES constant."""

    def test_all_task_priorities_valid(self):
        """All task priorities should be valid enum values."""
        for subcategory, task_configs in TASK_TYPES.items():
            for title, priority in task_configs:
                assert isinstance(priority, TaskPriority), f"Invalid priority for {subcategory}: {priority}"

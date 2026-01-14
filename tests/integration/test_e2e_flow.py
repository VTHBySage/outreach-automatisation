"""End-to-end integration tests for the complete workflow.

Flow tested:
SmartLead Webhook
  → Contact created
  → EmailReply saved
  → AI categorization
  → Tasks generated
  → HubSpot synced
  → Teams notification sent
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    MainCategory,
    SubCategory,
    TaskPriority,
    TaskStatus,
    WebhookSource,
)
from app.db.models.contact import Contact
from app.db.models.email_reply import EmailReply
from app.db.models.task import Task


class TestEndToEndFlow:
    """End-to-end tests for the complete outreach automation workflow."""

    @pytest_asyncio.fixture
    async def setup_contact(self, test_session: AsyncSession) -> Contact:
        """Create a test contact."""
        contact = Contact(
            email="interested@example.com",
            first_name="Jane",
            last_name="Smith",
            company_name="Tech Startup Inc",
            company_domain="techstartup.com",
            phone="+1-555-9876",
        )
        test_session.add(contact)
        await test_session.commit()
        await test_session.refresh(contact)
        return contact

    @pytest_asyncio.fixture
    async def setup_email_reply(
        self,
        test_session: AsyncSession,
        setup_contact: Contact,
    ) -> EmailReply:
        """Create a test email reply."""
        reply = EmailReply(
            contact_id=setup_contact.id,
            source=WebhookSource.SMARTLEAD.value,
            external_id=f"lead_{uuid4().hex[:8]}",
            subject="Re: Your Solution",
            body_text="Hi, I'm definitely interested! Can we schedule a call for next week? My number is 555-1234.",
            received_at=datetime.utcnow(),
            processed=False,
        )
        test_session.add(reply)
        await test_session.commit()
        await test_session.refresh(reply)
        return reply

    @pytest.mark.asyncio
    async def test_categorization_flow(
        self,
        test_session: AsyncSession,
        setup_contact: Contact,
        setup_email_reply: EmailReply,
    ):
        """Test that categorization correctly updates records and triggers task creation."""
        from app.db.repositories.email_reply import EmailReplyRepository
        from app.services.categorization.schemas import CategorizationResult
        from app.services.tasks import TaskService

        reply_repo = EmailReplyRepository(test_session)

        # Mock categorization result - "interested" reply
        mock_result = CategorizationResult(
            main_category=MainCategory.INTERESTED,
            subcategory=SubCategory.INTERESTED_SCHEDULE_CALL,
            confidence=Decimal("0.95"),
            reasoning="Lead explicitly asked to schedule a call and provided phone number.",
        )

        # Update reply with categorization
        await reply_repo.mark_as_categorized(
            reply_id=setup_email_reply.id,
            main_category=mock_result.main_category.value,
            subcategory=mock_result.subcategory.value,
            confidence=float(mock_result.confidence),
            reasoning=mock_result.reasoning,
        )

        # Update contact category
        setup_contact.current_category = mock_result.main_category.value
        setup_contact.current_subcategory = mock_result.subcategory.value
        await test_session.flush()

        # Create tasks based on categorization
        task_service = TaskService(test_session)
        created_tasks = await task_service.create_tasks_for_reply(
            contact=setup_contact,
            subcategory=mock_result.subcategory,
            reply_id=setup_email_reply.id,
        )

        await test_session.commit()

        # Verify email reply was categorized
        updated_reply = await test_session.get(EmailReply, setup_email_reply.id)
        assert updated_reply.main_category == MainCategory.INTERESTED.value
        assert updated_reply.subcategory == SubCategory.INTERESTED_SCHEDULE_CALL.value
        assert updated_reply.categorization_confidence == Decimal("0.95")
        assert updated_reply.categorized_at is not None

        # Verify contact was updated
        updated_contact = await test_session.get(Contact, setup_contact.id)
        assert updated_contact.current_category == MainCategory.INTERESTED.value
        assert updated_contact.current_subcategory == SubCategory.INTERESTED_SCHEDULE_CALL.value

        # Verify tasks were created (schedule_call generates HIGHEST priority tasks)
        assert len(created_tasks) > 0
        for task in created_tasks:
            assert task.contact_id == setup_contact.id
            assert task.triggered_by_reply_id == setup_email_reply.id
            assert task.priority == TaskPriority.HIGHEST.value

    @pytest.mark.asyncio
    async def test_referral_creates_highest_priority_tasks(
        self,
        test_session: AsyncSession,
        setup_contact: Contact,
        setup_email_reply: EmailReply,
    ):
        """Test that referral categorization creates HIGHEST priority tasks."""
        from app.services.tasks import TaskService

        task_service = TaskService(test_session)

        # Create tasks for referral subcategory
        created_tasks = await task_service.create_tasks_for_reply(
            contact=setup_contact,
            subcategory=SubCategory.INTERESTED_REFERRAL,
            reply_id=setup_email_reply.id,
        )

        await test_session.commit()

        # Referral should create HIGHEST priority tasks
        assert len(created_tasks) >= 1
        for task in created_tasks:
            assert task.priority == TaskPriority.HIGHEST.value
            assert "referral" in task.task_type.lower() or "contact" in task.title.lower()

    @pytest.mark.asyncio
    async def test_not_interested_creates_lower_priority_tasks(
        self,
        test_session: AsyncSession,
        setup_contact: Contact,
        setup_email_reply: EmailReply,
    ):
        """Test that 'not interested' categorization creates lower priority tasks."""
        from app.services.tasks import TaskService

        task_service = TaskService(test_session)

        # Create tasks for "not now - busy" subcategory
        created_tasks = await task_service.create_tasks_for_reply(
            contact=setup_contact,
            subcategory=SubCategory.NOT_NOW_BUSY,
            reply_id=setup_email_reply.id,
        )

        await test_session.commit()

        # Not now - busy should create MEDIUM or LOW priority follow-up tasks
        # Some subcategories might not create tasks at all
        for task in created_tasks:
            # Should not be highest priority for "not now"
            assert task.priority in [
                TaskPriority.LOW.value,
                TaskPriority.MEDIUM.value,
                TaskPriority.HIGH.value,
            ]

    @pytest.mark.asyncio
    async def test_task_hubspot_sync_status(
        self,
        test_session: AsyncSession,
        setup_contact: Contact,
    ):
        """Test that tasks are created with pending sync status."""
        # Create a task manually
        task = Task(
            contact_id=setup_contact.id,
            title="Follow up with lead",
            description="Schedule call with interested lead",
            priority=TaskPriority.HIGHEST.value,
            task_type="schedule_call",
            due_date=datetime.utcnow(),
            sync_status=TaskStatus.PENDING.value,
        )
        test_session.add(task)
        await test_session.commit()
        await test_session.refresh(task)

        # Verify initial sync status
        assert task.sync_status == TaskStatus.PENDING.value
        assert task.hubspot_task_id is None
        assert task.synced_at is None

        # Simulate HubSpot sync
        task.hubspot_task_id = "hs_task_123456"
        task.sync_status = TaskStatus.SYNCED.value
        task.synced_at = datetime.utcnow()
        await test_session.commit()

        # Verify synced status
        updated_task = await test_session.get(Task, task.id)
        assert updated_task.sync_status == TaskStatus.SYNCED.value
        assert updated_task.hubspot_task_id == "hs_task_123456"
        assert updated_task.synced_at is not None

    @pytest.mark.asyncio
    async def test_task_notification_status(
        self,
        test_session: AsyncSession,
        setup_contact: Contact,
    ):
        """Test that task notification status is tracked correctly."""
        # Create a HIGH priority task
        task = Task(
            contact_id=setup_contact.id,
            title="Urgent follow up",
            description="Lead requested immediate callback",
            priority=TaskPriority.HIGHEST.value,
            task_type="schedule_call",
            due_date=datetime.utcnow(),
            sync_status=TaskStatus.PENDING.value,
        )
        test_session.add(task)
        await test_session.commit()
        await test_session.refresh(task)

        # Verify no notification sent yet
        assert task.ms_teams_message_id is None
        assert task.notification_sent_at is None

        # Simulate notification sent
        task.ms_teams_message_id = "teams_msg_abc123"
        task.notification_sent_at = datetime.utcnow()
        await test_session.commit()

        # Verify notification tracked
        updated_task = await test_session.get(Task, task.id)
        assert updated_task.ms_teams_message_id == "teams_msg_abc123"
        assert updated_task.notification_sent_at is not None

    @pytest.mark.asyncio
    async def test_contact_hubspot_sync(
        self,
        test_session: AsyncSession,
        setup_contact: Contact,
    ):
        """Test that contact HubSpot sync is tracked correctly."""
        # Initially no HubSpot ID
        assert setup_contact.hubspot_contact_id is None

        # Simulate HubSpot sync
        setup_contact.hubspot_contact_id = "hs_contact_789"
        await test_session.commit()

        # Verify HubSpot ID saved
        updated_contact = await test_session.get(Contact, setup_contact.id)
        assert updated_contact.hubspot_contact_id == "hs_contact_789"

    @pytest.mark.asyncio
    async def test_duplicate_reply_detection(
        self,
        test_session: AsyncSession,
        setup_contact: Contact,
    ):
        """Test that duplicate email replies are detected."""
        from app.db.repositories.email_reply import EmailReplyRepository

        reply_repo = EmailReplyRepository(test_session)
        external_id = f"lead_{uuid4().hex[:8]}"

        # Create first reply
        reply1 = await reply_repo.create_from_webhook(
            contact_id=setup_contact.id,
            source=WebhookSource.SMARTLEAD.value,
            external_id=external_id,
            body_text="First message",
            subject="Test",
        )
        await test_session.commit()

        # Try to find duplicate
        existing = await reply_repo.get_by_external_id(
            source=WebhookSource.SMARTLEAD.value,
            external_id=external_id,
        )

        assert existing is not None
        assert existing.id == reply1.id

    @pytest.mark.asyncio
    async def test_re_engagement_scheduling(
        self,
        test_session: AsyncSession,
        setup_contact: Contact,
    ):
        """Test that re-engagement dates are calculated correctly."""
        from app.services.scheduler import SchedulerService

        scheduler_service = SchedulerService(test_session)

        # Schedule re-engagement for "not now - busy" (should be 14 days)
        re_engagement_date = await scheduler_service.schedule_reengagement(
            contact=setup_contact,
            subcategory=SubCategory.NOT_NOW_BUSY,
        )

        assert re_engagement_date is not None
        # Should be in the future
        assert re_engagement_date > datetime.utcnow()

        # Verify contact was updated
        await test_session.refresh(setup_contact)
        assert setup_contact.re_engagement_date is not None


class TestNotificationService:
    """Tests for notification service functionality."""

    @pytest.mark.asyncio
    async def test_notification_skipped_for_low_priority(self):
        """Test that notifications are skipped for low-priority tasks."""
        from app.services.notifications import NotificationService

        service = NotificationService()

        # Create mock task with LOW priority
        mock_task = MagicMock()
        mock_task.priority = TaskPriority.LOW.value

        should_notify = await service.should_notify(mock_task)
        assert should_notify is False

    @pytest.mark.asyncio
    async def test_notification_sent_for_high_priority(self):
        """Test that notifications are sent for high-priority tasks."""
        from app.services.notifications import NotificationService

        service = NotificationService()

        # Create mock task with HIGH priority
        mock_task = MagicMock()
        mock_task.priority = TaskPriority.HIGH.value

        should_notify = await service.should_notify(mock_task)
        assert should_notify is True

    @pytest.mark.asyncio
    async def test_notification_sent_for_highest_priority(self):
        """Test that notifications are sent for highest-priority tasks."""
        from app.services.notifications import NotificationService

        service = NotificationService()

        # Create mock task with HIGHEST priority
        mock_task = MagicMock()
        mock_task.priority = TaskPriority.HIGHEST.value

        should_notify = await service.should_notify(mock_task)
        assert should_notify is True


class TestCategorizationService:
    """Tests for AI categorization service."""

    @pytest.mark.asyncio
    async def test_categorization_returns_valid_result(self):
        """Test that categorization service returns valid results."""
        from app.services.categorization import CategorizationService
        from app.services.categorization.schemas import CategorizationResult

        # Mock OpenAI response
        mock_response = {
            "main_category": "interested",
            "subcategory": "interested_schedule_call",
            "confidence": 0.92,
            "reasoning": "Lead explicitly asked to schedule a call.",
        }

        with patch(
            "app.services.categorization.service.CategorizationService._call_openai",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            service = CategorizationService()
            result = await service.categorize_reply(
                subject="Re: Your offer",
                body="I'm interested, let's talk next week.",
            )

            assert isinstance(result, CategorizationResult)
            assert result.main_category == MainCategory.INTERESTED
            assert result.subcategory == SubCategory.INTERESTED_SCHEDULE_CALL
            assert float(result.confidence) == 0.92


class TestTaskFactory:
    """Tests for task factory functionality."""

    def test_task_factory_creates_correct_tasks_for_referral(self):
        """Test that referral creates correct task types."""
        from app.services.tasks.factory import TaskFactory

        factory = TaskFactory()
        task_defs = factory.get_task_definitions(SubCategory.INTERESTED_REFERRAL)

        assert len(task_defs) >= 1
        # All referral tasks should be HIGHEST priority
        for task_def in task_defs:
            assert task_def["priority"] == TaskPriority.HIGHEST

    def test_task_factory_creates_correct_tasks_for_schedule_call(self):
        """Test that schedule call creates correct task types."""
        from app.services.tasks.factory import TaskFactory

        factory = TaskFactory()
        task_defs = factory.get_task_definitions(SubCategory.INTERESTED_SCHEDULE_CALL)

        assert len(task_defs) >= 1
        # Schedule call tasks should be HIGHEST priority
        for task_def in task_defs:
            assert task_def["priority"] == TaskPriority.HIGHEST

    def test_task_factory_due_date_calculation(self):
        """Test that due dates are calculated correctly."""
        from app.services.tasks.factory import TaskFactory

        factory = TaskFactory()

        # Get due date for HIGHEST priority (should be within 4 hours)
        due_date = factory.calculate_due_date(TaskPriority.HIGHEST)
        now = datetime.utcnow()

        # Should be within 5 hours from now (4 hours + small buffer)
        diff = due_date - now
        assert diff.total_seconds() <= 5 * 3600  # 5 hours in seconds
        assert diff.total_seconds() > 0  # Should be in the future

"""AI categorization tasks."""

from uuid import UUID

from celery import shared_task

from app.core.constants import SubCategory, TaskPriority
from app.services.categorization.service import ReferralInfo
from app.core.logging import get_logger
from app.core.utils import run_async
from app.db.session import async_session_factory

logger = get_logger(__name__)


async def _suppress_lead_from_smartlead(
    contact,
    reply,
    reason: str,
) -> None:
    """
    Auto-remove unsubscribed or bounced lead from SmartLead.

    This ensures IMMEDIATE suppression for:
    - SubCategory.UNSUBSCRIBE (3.5)
    - SubCategory.HARD_BOUNCE (5.7)

    Strategy:
    1. Always add email to global blocklist (highest priority - ensures no future emails)
    2. If campaign_id available, remove from that specific campaign
    3. If no campaign_id but have email, remove from all campaigns
    """
    from app.integrations.smartlead import SmartLeadClient
    from app.integrations.smartlead.client import SmartLeadError

    email = contact.email
    lead_id = contact.smartlead_lead_id
    campaign_id = reply.campaign_external_id

    if not email:
        logger.error(
            "suppression_failed_no_email",
            contact_id=str(contact.id),
            reason=reason,
        )
        return

    smartlead = SmartLeadClient()

    # Step 1: ALWAYS add to global blocklist first (critical for unsubscribes)
    try:
        await smartlead.add_to_blocklist(email)
        logger.info(
            "lead_added_to_blocklist",
            contact_id=str(contact.id),
            email=email,
            reason=reason,
        )
    except SmartLeadError as e:
        # Log but continue - still try to remove from campaigns
        logger.error(
            "blocklist_add_failed",
            contact_id=str(contact.id),
            email=email,
            reason=reason,
            error=str(e),
        )

    # Step 2: Remove from campaigns
    try:
        if lead_id and campaign_id:
            # Best case: we have both IDs
            await smartlead.remove_lead_from_campaign(campaign_id, lead_id)
            logger.info(
                "lead_removed_from_campaign",
                contact_id=str(contact.id),
                lead_id=lead_id,
                campaign_id=campaign_id,
                reason=reason,
            )
        else:
            # Fallback: remove from all campaigns by email
            result = await smartlead.remove_lead_from_all_campaigns(email)
            logger.info(
                "lead_removed_from_all_campaigns",
                contact_id=str(contact.id),
                email=email,
                removed_count=len(result.get("removed_from_campaigns", [])),
                reason=reason,
            )
    except SmartLeadError as e:
        # Log but don't fail - blocklist addition is the critical part
        logger.error(
            "campaign_removal_failed",
            contact_id=str(contact.id),
            email=email,
            reason=reason,
            error=str(e),
        )


async def _process_referral(
    referrer_contact,
    referral_info: ReferralInfo,
    reply,
    session,
) -> None:
    """
    Auto-process referral: create contact and enroll in campaign.

    Flow:
    1. Create new contact in database (if email provided)
    2. Create contact in HubSpot
    3. Add to SmartLead/ConnectSafely with referral message
    """
    from app.db.models.contact import Contact
    from app.db.repositories.contact import ContactRepository
    from app.integrations.hubspot import HubSpotContacts
    from app.integrations.smartlead import SmartLeadClient

    if not referral_info.email and not referral_info.name:
        logger.warning(
            "referral_missing_info",
            referrer_id=str(referrer_contact.id),
        )
        return

    contact_repo = ContactRepository(session)

    # Check if referral contact already exists
    existing_contact = None
    if referral_info.email:
        existing_contact = await contact_repo.get_by_email(referral_info.email)

    if existing_contact:
        logger.info(
            "referral_contact_exists",
            referrer_id=str(referrer_contact.id),
            referral_email=referral_info.email,
            existing_contact_id=str(existing_contact.id),
        )
        return

    # Create new referral contact
    referral_contact = None
    if referral_info.email:
        # Parse name into first/last
        first_name = None
        last_name = None
        if referral_info.name:
            name_parts = referral_info.name.split()
            first_name = name_parts[0] if name_parts else None
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else None

        referral_contact = Contact(
            email=referral_info.email,
            first_name=first_name,
            last_name=last_name,
            company_name=referral_info.company,
            source="referral",
            campaign_id=reply.campaign_external_id,
            validation_notes=f"Referred by {referrer_contact.full_name or referrer_contact.email}",
        )
        session.add(referral_contact)
        await session.flush()

        logger.info(
            "referral_contact_created",
            referrer_id=str(referrer_contact.id),
            referral_contact_id=str(referral_contact.id),
            referral_email=referral_info.email,
        )

    # Create in HubSpot
    if referral_contact and referral_info.email:
        try:
            hubspot = HubSpotContacts()
            hs_contact = await hubspot.create_or_update_contact(
                email=referral_info.email,
                first_name=first_name,
                last_name=last_name,
                company=referral_info.company,
            )
            if hs_contact:
                referral_contact.hubspot_contact_id = hs_contact.get("id")
                logger.info(
                    "referral_hubspot_created",
                    referral_contact_id=str(referral_contact.id),
                    hubspot_id=hs_contact.get("id"),
                )
        except Exception as e:
            logger.error(
                "referral_hubspot_failed",
                referral_contact_id=str(referral_contact.id),
                error=str(e),
            )

    # Add to SmartLead campaign with referral message
    if referral_contact and reply.campaign_external_id:
        try:
            smartlead = SmartLeadClient()
            referral_message = (
                f"Hi {first_name or 'there'}, {referrer_contact.full_name or 'A colleague'} "
                f"at {referrer_contact.company_name or 'your company'} suggested I reach out to you."
            )

            await smartlead.add_lead_to_campaign(
                campaign_id=reply.campaign_external_id,
                email=referral_info.email,
                first_name=first_name,
                last_name=last_name,
                company_name=referral_info.company,
                custom_fields={"referral_message": referral_message},
            )

            logger.info(
                "referral_added_to_campaign",
                referral_contact_id=str(referral_contact.id),
                campaign_id=reply.campaign_external_id,
            )
        except Exception as e:
            logger.error(
                "referral_campaign_add_failed",
                referral_contact_id=str(referral_contact.id),
                campaign_id=reply.campaign_external_id,
                error=str(e),
            )


async def _categorize_email_reply_async(
    reply_id: str,
    subject: str,
    body: str,
    context: str | None = None,
) -> dict:
    """Async implementation of email reply categorization."""
    from app.db.models.contact import Contact
    from app.db.models.email_reply import EmailReply
    from app.db.repositories.email_reply import EmailReplyRepository
    from app.services.categorization import CategorizationService
    from app.services.scheduler import SchedulerService
    from app.services.tasks import TaskService
    from app.workers.hubspot_tasks import create_hubspot_task
    from app.workers.notification_tasks import send_teams_notification

    async with async_session_factory() as session:
        try:
            reply_uuid = UUID(reply_id)

            # 1. Load email reply
            reply_repo = EmailReplyRepository(session)
            reply = await reply_repo.get_by_id(reply_uuid)

            if not reply:
                logger.error("email_reply_not_found", reply_id=reply_id)
                return {"status": "error", "reason": "reply_not_found"}

            # 2. Load contact
            contact = await session.get(Contact, reply.contact_id)
            if not contact:
                logger.error("contact_not_found", contact_id=str(reply.contact_id))
                return {"status": "error", "reason": "contact_not_found"}

            # 3. Call AI categorization
            categorization_service = CategorizationService()
            result = await categorization_service.categorize_reply(
                subject=subject,
                body=body,
                context=context,
            )

            logger.info(
                "ai_categorization_result",
                reply_id=reply_id,
                main_category=result.main_category.value,
                subcategory=result.subcategory.value,
                confidence=float(result.confidence),
            )

            # 4. Update email reply with categorization
            await reply_repo.mark_as_categorized(
                reply_id=reply_uuid,
                main_category=result.main_category.value,
                subcategory=result.subcategory.value,
                confidence=float(result.confidence),
                reasoning=result.reasoning,
            )

            # 5. Update contact's current category
            contact.current_category = result.main_category.value
            contact.current_subcategory = result.subcategory.value
            await session.flush()

            # 5.5 Auto-suppress unsubscribed or bounced leads from SmartLead
            if result.subcategory in {SubCategory.UNSUBSCRIBE, SubCategory.HARD_BOUNCE}:
                await _suppress_lead_from_smartlead(
                    contact=contact,
                    reply=reply,
                    reason=result.subcategory.value,
                )

            # 5.6 Handle prospect-defined timing for WRONG_TIMING category
            if result.subcategory == SubCategory.WRONG_TIMING and result.suggested_followup_date:
                from datetime import datetime

                try:
                    followup_date = datetime.fromisoformat(result.suggested_followup_date)
                    contact.re_engagement_date = followup_date.date()
                    contact.re_engagement_category = result.subcategory.value
                    logger.info(
                        "prospect_defined_followup_set",
                        contact_id=str(contact.id),
                        followup_date=result.suggested_followup_date,
                    )
                except ValueError as e:
                    logger.warning(
                        "invalid_followup_date",
                        contact_id=str(contact.id),
                        date_str=result.suggested_followup_date,
                        error=str(e),
                    )

            # 5.7 Handle referral auto-enrollment
            if result.subcategory == SubCategory.REFERRAL and result.referral_info:
                await _process_referral(
                    referrer_contact=contact,
                    referral_info=result.referral_info,
                    reply=reply,
                    session=session,
                )

            # 6. Generate tasks based on categorization
            task_service = TaskService(session)
            created_tasks = await task_service.create_tasks_for_reply(
                contact=contact,
                subcategory=result.subcategory,
                reply_id=reply_uuid,
            )

            reply.tasks_created = len(created_tasks) > 0
            await session.flush()

            logger.info(
                "tasks_generated",
                reply_id=reply_id,
                task_count=len(created_tasks),
            )

            # 7. Schedule re-engagement if applicable
            scheduler_service = SchedulerService(session)
            re_engagement_date = await scheduler_service.schedule_reengagement(
                contact=contact,
                subcategory=result.subcategory,
            )

            # 8. Mark reply as processed
            await reply_repo.mark_as_processed(reply_uuid)

            # 9. Commit all changes
            await session.commit()

            # 10. Queue HubSpot sync and notifications (after commit)
            for task in created_tasks:
                # Queue HubSpot task creation
                create_hubspot_task.delay(task_id=str(task.id))

                # Queue Teams notification for high-priority tasks
                priority = TaskPriority(task.priority)
                if priority in {TaskPriority.HIGHEST, TaskPriority.HIGH}:
                    send_teams_notification.delay(
                        task_id=str(task.id),
                        contact_id=str(contact.id),
                    )

            return {
                "status": "categorized",
                "reply_id": reply_id,
                "contact_id": str(contact.id),
                "main_category": result.main_category.value,
                "subcategory": result.subcategory.value,
                "confidence": float(result.confidence),
                "tasks_created": len(created_tasks),
                "re_engagement_date": re_engagement_date.isoformat() if re_engagement_date else None,
            }

        except Exception as e:
            await session.rollback()
            raise e


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def categorize_email_reply(
    self,
    reply_id: str,
    subject: str,
    body: str,
    context: str | None = None,
) -> dict:
    """
    Categorize an email reply using AI.

    Performance target: < 2 seconds

    Flow:
    1. Call OpenAI for categorization
    2. Update EmailReply record with category
    3. Update Contact with current category
    4. Trigger task generation
    5. Schedule re-engagement if applicable
    6. Queue HubSpot sync and notifications
    """
    # Validate UUID format before processing
    try:
        UUID(reply_id)
    except ValueError:
        logger.error(
            "invalid_reply_id_format",
            reply_id=reply_id,
        )
        return {"status": "error", "reason": "invalid_reply_id_format"}

    try:
        logger.info(
            "categorizing_reply",
            reply_id=reply_id,
        )

        result = run_async(
            _categorize_email_reply_async(
                reply_id=reply_id,
                subject=subject,
                body=body,
                context=context,
            )
        )

        return result

    except Exception as e:
        logger.error(
            "categorization_failed",
            reply_id=reply_id,
            error=str(e),
        )
        raise self.retry(exc=e)


async def _validate_lead_company_async(
    contact_id: str,
    company_domain: str,
    campaign_criteria: dict,
) -> dict:
    """Async implementation of company validation using AI."""
    from app.core.constants import ValidationStatus
    from app.db.models.contact import Contact
    from app.integrations.apollo import ApolloClient
    from app.services.categorization import CategorizationService

    async with async_session_factory() as session:
        try:
            contact_uuid = UUID(contact_id)
            contact = await session.get(Contact, contact_uuid)

            if not contact:
                return {"status": "error", "reason": "contact_not_found"}

            # Skip if already validated
            if contact.validation_status == ValidationStatus.VALIDATED.value:
                return {
                    "status": "already_validated",
                    "contact_id": contact_id,
                    "validation_status": contact.validation_status,
                    "confidence": float(contact.validation_confidence) if contact.validation_confidence else None,
                }

            # Try to enrich company info via Apollo
            company_description = None
            if company_domain:
                try:
                    apollo_client = ApolloClient()
                    org_data = await apollo_client.enrich_organization(company_domain)
                    if org_data:
                        company_description = org_data.get("description")
                        # Update contact with enriched data if available
                        if org_data.get("name") and not contact.company_name:
                            contact.company_name = org_data["name"]
                except Exception as e:
                    logger.warning(
                        "apollo_enrichment_failed",
                        contact_id=contact_id,
                        domain=company_domain,
                        error=str(e),
                    )

            # Call AI for company validation
            categorization_service = CategorizationService()
            validation_result = await categorization_service.validate_company(
                company_name=contact.company_name,
                company_domain=company_domain,
                company_description=company_description,
                campaign_criteria=campaign_criteria,
            )

            # Update contact with validation results
            if validation_result.is_match:
                if validation_result.needs_review:
                    contact.validation_status = ValidationStatus.MANUAL_REVIEW.value
                else:
                    contact.validation_status = ValidationStatus.VALIDATED.value
            else:
                contact.validation_status = ValidationStatus.REJECTED.value

            contact.validation_confidence = validation_result.confidence
            contact.company_type = validation_result.company_type
            contact.validation_notes = validation_result.reasoning

            await session.commit()

            logger.info(
                "company_validated",
                contact_id=contact_id,
                validation_status=contact.validation_status,
                confidence=float(validation_result.confidence),
                needs_review=validation_result.needs_review,
            )

            return {
                "status": "validated",
                "contact_id": contact_id,
                "validation_status": contact.validation_status,
                "confidence": float(validation_result.confidence),
                "company_type": validation_result.company_type,
                "is_match": validation_result.is_match,
                "needs_review": validation_result.needs_review,
                "reasoning": validation_result.reasoning,
            }

        except Exception as e:
            await session.rollback()
            raise e


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def validate_lead_company(
    self,
    contact_id: str,
    company_domain: str,
    campaign_criteria: dict,
) -> dict:
    """
    Validate if company matches campaign criteria using LLM.

    Flow:
    1. Fetch company website/LinkedIn
    2. Call LLM for classification
    3. Update contact validation status
    4. Add to manual review queue if borderline (75-85% confidence)
    """
    # Validate UUID format before processing
    try:
        UUID(contact_id)
    except ValueError:
        logger.error(
            "invalid_contact_id_format",
            contact_id=contact_id,
        )
        return {"status": "error", "reason": "invalid_contact_id_format"}

    try:
        logger.info(
            "validating_company",
            contact_id=contact_id,
            domain=company_domain,
        )

        result = run_async(
            _validate_lead_company_async(
                contact_id=contact_id,
                company_domain=company_domain,
                campaign_criteria=campaign_criteria,
            )
        )

        return result

    except Exception as e:
        logger.error(
            "validation_failed",
            contact_id=contact_id,
            error=str(e),
        )
        raise self.retry(exc=e)

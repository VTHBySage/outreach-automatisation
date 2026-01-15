"""GDPR compliance API endpoints for data export and deletion."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import delete, select

from app.api.v1.schemas import MessageResponse
from app.core.logging import get_logger
from app.db.models.contact import Contact
from app.db.models.email_reply import EmailReply
from app.db.models.task import Task
from app.db.models.webhook_log import WebhookLog
from app.dependencies import DbSession

logger = get_logger(__name__)
router = APIRouter()


@router.get("/export/{contact_id}")
async def export_contact_data(
    session: DbSession,
    contact_id: UUID,
):
    """
    Export all data associated with a contact (GDPR Data Subject Access Request).

    Returns all personal data stored for the contact including:
    - Contact information
    - Email replies and categorizations
    - Tasks
    - Webhook logs

    This endpoint supports GDPR Article 15 (Right of Access) and
    Article 20 (Right to Data Portability).
    """
    # Get contact
    contact = await session.get(Contact, contact_id)

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    # Get all email replies
    replies_result = await session.execute(
        select(EmailReply).where(EmailReply.contact_id == contact_id)
    )
    replies = replies_result.scalars().all()

    # Get all tasks
    tasks_result = await session.execute(
        select(Task).where(Task.contact_id == contact_id)
    )
    tasks = tasks_result.scalars().all()

    # Get webhook logs related to this contact (by email)
    webhook_logs_result = await session.execute(
        select(WebhookLog).where(
            WebhookLog.payload.cast(str).contains(contact.email)
        ).limit(100)
    )
    webhook_logs = webhook_logs_result.scalars().all()

    # Build export data
    export_data = {
        "export_date": datetime.utcnow().isoformat(),
        "data_subject_id": str(contact_id),
        "contact": {
            "id": str(contact.id),
            "email": contact.email,
            "first_name": contact.first_name,
            "last_name": contact.last_name,
            "phone": contact.phone,
            "linkedin_url": contact.linkedin_url,
            "company_name": contact.company_name,
            "company_domain": contact.company_domain,
            "company_type": contact.company_type,
            "validation_status": contact.validation_status,
            "validation_confidence": float(contact.validation_confidence) if contact.validation_confidence else None,
            "validation_notes": contact.validation_notes,
            "source": contact.source,
            "campaign_id": contact.campaign_id,
            "current_category": contact.current_category,
            "current_subcategory": contact.current_subcategory,
            "last_contacted_at": contact.last_contacted_at.isoformat() if contact.last_contacted_at else None,
            "last_response_at": contact.last_response_at.isoformat() if contact.last_response_at else None,
            "re_engagement_date": contact.re_engagement_date.isoformat() if contact.re_engagement_date else None,
            "re_engagement_category": contact.re_engagement_category,
            "hubspot_contact_id": contact.hubspot_contact_id,
            "apollo_id": contact.apollo_id,
            "smartlead_lead_id": contact.smartlead_lead_id,
            "created_at": contact.created_at.isoformat() if contact.created_at else None,
            "updated_at": contact.updated_at.isoformat() if contact.updated_at else None,
            "deleted_at": contact.deleted_at.isoformat() if contact.deleted_at else None,
        },
        "email_replies": [
            {
                "id": str(reply.id),
                "source": reply.source,
                "external_id": reply.external_id,
                "campaign_external_id": reply.campaign_external_id,
                "subject": reply.subject,
                "body_text": reply.body_text,
                "received_at": reply.received_at.isoformat() if reply.received_at else None,
                "main_category": reply.main_category,
                "subcategory": reply.subcategory,
                "categorization_confidence": float(reply.categorization_confidence) if reply.categorization_confidence else None,
                "categorization_reasoning": reply.categorization_reasoning,
                "categorized_at": reply.categorized_at.isoformat() if reply.categorized_at else None,
                "processed": reply.processed,
                "created_at": reply.created_at.isoformat() if reply.created_at else None,
            }
            for reply in replies
        ],
        "tasks": [
            {
                "id": str(task.id),
                "title": task.title,
                "description": task.description,
                "priority": task.priority,
                "category": task.category,
                "subcategory": task.subcategory,
                "task_type": task.task_type,
                "assigned_to": task.assigned_to,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "hubspot_task_id": task.hubspot_task_id,
                "sync_status": task.sync_status,
                "created_at": task.created_at.isoformat() if task.created_at else None,
            }
            for task in tasks
        ],
        "webhook_events": [
            {
                "id": str(log.id),
                "source": log.source,
                "received_at": log.received_at.isoformat() if log.received_at else None,
            }
            for log in webhook_logs
        ],
        "metadata": {
            "total_email_replies": len(replies),
            "total_tasks": len(tasks),
            "total_webhook_events": len(webhook_logs),
        },
    }

    logger.info(
        "gdpr_data_exported",
        contact_id=str(contact_id),
        email=contact.email,
        replies_count=len(replies),
        tasks_count=len(tasks),
    )

    return JSONResponse(
        content=export_data,
        headers={
            "Content-Disposition": f"attachment; filename=contact_{contact_id}_export.json",
        },
    )


@router.delete("/delete/{contact_id}", response_model=MessageResponse)
async def delete_contact_data(
    session: DbSession,
    contact_id: UUID,
    hard_delete: bool = False,
):
    """
    Delete all data associated with a contact (GDPR Right to Erasure).

    By default, performs a soft delete (sets deleted_at timestamp).
    Set hard_delete=true to permanently remove all data.

    This endpoint supports GDPR Article 17 (Right to Erasure / Right to be Forgotten).

    WARNING: Hard delete is irreversible and removes all associated data including:
    - Contact record
    - All email replies
    - All tasks
    - Related webhook logs
    """
    # Get contact
    contact = await session.get(Contact, contact_id)

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    if hard_delete:
        # Hard delete - permanently remove all data
        email_for_log = contact.email

        # Delete webhook logs mentioning this contact
        await session.execute(
            delete(WebhookLog).where(
                WebhookLog.payload.cast(str).contains(contact.email)
            )
        )

        # Delete tasks (cascade will handle if not set)
        await session.execute(
            delete(Task).where(Task.contact_id == contact_id)
        )

        # Delete email replies (cascade will handle if not set)
        await session.execute(
            delete(EmailReply).where(EmailReply.contact_id == contact_id)
        )

        # Delete contact
        await session.delete(contact)
        await session.flush()

        logger.info(
            "gdpr_hard_delete",
            contact_id=str(contact_id),
            email=email_for_log,
        )

        return MessageResponse(
            message="Contact and all associated data permanently deleted",
            success=True,
        )

    else:
        # Soft delete - just mark as deleted
        contact.deleted_at = datetime.utcnow()

        # Anonymize PII fields
        contact.first_name = "[DELETED]"
        contact.last_name = "[DELETED]"
        contact.phone = None
        contact.linkedin_url = None
        contact.validation_notes = None

        await session.flush()

        logger.info(
            "gdpr_soft_delete",
            contact_id=str(contact_id),
        )

        return MessageResponse(
            message="Contact soft deleted and PII anonymized",
            success=True,
        )


@router.get("/retention-policy")
async def get_retention_policy():
    """
    Get data retention policy information.

    Returns information about how long different types of data are retained.
    """
    return {
        "policy_version": "1.0",
        "last_updated": "2024-01-01",
        "retention_periods": {
            "contact_data": {
                "active_contacts": "Indefinite while relationship exists",
                "soft_deleted_contacts": "90 days",
                "hard_deleted_contacts": "Immediate removal",
            },
            "email_replies": {
                "retention": "2 years",
                "purpose": "Business communication records",
            },
            "task_records": {
                "retention": "2 years",
                "purpose": "Business process records",
            },
            "webhook_logs": {
                "retention": "30 days",
                "purpose": "System debugging and audit",
            },
        },
        "legal_basis": [
            "Legitimate business interest (B2B communications)",
            "Contract performance",
            "Legal obligation (business records)",
        ],
        "data_subject_rights": [
            "Right of access (GET /gdpr/export/{contact_id})",
            "Right to erasure (DELETE /gdpr/delete/{contact_id})",
            "Right to rectification (PATCH /contacts/{contact_id})",
            "Right to data portability (GET /gdpr/export/{contact_id})",
        ],
    }

"""Application constants and enums."""

from enum import Enum


class MainCategory(str, Enum):
    """Main response categories (5 mother categories)."""

    INTERESTED = "interested"
    POSITIVE_SIGNALS = "positive_signals"
    NOT_INTERESTED = "not_interested"
    NEGATIVE_SIGNALS = "negative_signals"
    AUTOMATE_REPLY = "automate_reply"


class SubCategory(str, Enum):
    """Response subcategories (26 total)."""

    # Interested (1.x)
    READY_TO_CHAT_PHONE = "1.1_ready_to_chat_phone"
    INTRIGUED = "1.2_intrigued"
    READY_TO_CHAT_OPEN = "1.3_ready_to_chat_open"
    CONNECT_WITH_ANOTHER = "1.4_connect_with_another"
    MISUNDERSTOOD_INTERESTED = "1.5_misunderstood_interested"
    LONG_TERM_FOLLOWUP = "1.6_long_term_followup"
    PROSPECT_PITCHING = "1.7_prospect_pitching"

    # Positive Signals (2.x)
    REFERRAL = "2.1_referral"
    COMPETITOR_MENTION = "2.2_competitor_mention"
    BUDGET_CONFIRMED = "2.3_budget_confirmed"
    AUTHORITY_CONFIRMED = "2.4_authority_confirmed"

    # Not Interested (3.x)
    MISTAKE_WRONG_COMPANY = "3.1_mistake_wrong_company"
    NOT_INTERESTED = "3.2_not_interested"
    SELF_DISQUALIFY = "3.3_self_disqualify"
    MISUNDERSTOOD_NOT_INTERESTED = "3.4_misunderstood_not_interested"
    UNSUBSCRIBE = "3.5_unsubscribe"

    # Negative Signals (4.x)
    HAPPY_WITH_COMPETITOR = "4.1_happy_with_competitor"
    RECENT_PURCHASE = "4.2_recent_purchase"
    WRONG_TIMING = "4.3_wrong_timing"

    # Automate Reply (5.x)
    OUT_OF_OFFICE = "5.1_out_of_office"
    NO_LONGER_WORKS_HERE = "5.2_no_longer_works_here"
    AUTO_ACKNOWLEDGE = "5.3_auto_acknowledge"
    AUTO_FORWARD = "5.4_auto_forward"
    AUTO_REPLY_CONNECT = "5.5_auto_reply_connect"
    EMPTY_REPLY = "5.6_empty_reply"
    HARD_BOUNCE = "5.7_hard_bounce"


# Mapping subcategories to main categories
SUBCATEGORY_TO_MAIN: dict[SubCategory, MainCategory] = {
    # Interested
    SubCategory.READY_TO_CHAT_PHONE: MainCategory.INTERESTED,
    SubCategory.INTRIGUED: MainCategory.INTERESTED,
    SubCategory.READY_TO_CHAT_OPEN: MainCategory.INTERESTED,
    SubCategory.CONNECT_WITH_ANOTHER: MainCategory.INTERESTED,
    SubCategory.MISUNDERSTOOD_INTERESTED: MainCategory.INTERESTED,
    SubCategory.LONG_TERM_FOLLOWUP: MainCategory.INTERESTED,
    SubCategory.PROSPECT_PITCHING: MainCategory.INTERESTED,
    # Positive Signals
    SubCategory.REFERRAL: MainCategory.POSITIVE_SIGNALS,
    SubCategory.COMPETITOR_MENTION: MainCategory.POSITIVE_SIGNALS,
    SubCategory.BUDGET_CONFIRMED: MainCategory.POSITIVE_SIGNALS,
    SubCategory.AUTHORITY_CONFIRMED: MainCategory.POSITIVE_SIGNALS,
    # Not Interested
    SubCategory.MISTAKE_WRONG_COMPANY: MainCategory.NOT_INTERESTED,
    SubCategory.NOT_INTERESTED: MainCategory.NOT_INTERESTED,
    SubCategory.SELF_DISQUALIFY: MainCategory.NOT_INTERESTED,
    SubCategory.MISUNDERSTOOD_NOT_INTERESTED: MainCategory.NOT_INTERESTED,
    SubCategory.UNSUBSCRIBE: MainCategory.NOT_INTERESTED,
    # Negative Signals
    SubCategory.HAPPY_WITH_COMPETITOR: MainCategory.NEGATIVE_SIGNALS,
    SubCategory.RECENT_PURCHASE: MainCategory.NEGATIVE_SIGNALS,
    SubCategory.WRONG_TIMING: MainCategory.NEGATIVE_SIGNALS,
    # Automate Reply
    SubCategory.OUT_OF_OFFICE: MainCategory.AUTOMATE_REPLY,
    SubCategory.NO_LONGER_WORKS_HERE: MainCategory.AUTOMATE_REPLY,
    SubCategory.AUTO_ACKNOWLEDGE: MainCategory.AUTOMATE_REPLY,
    SubCategory.AUTO_FORWARD: MainCategory.AUTOMATE_REPLY,
    SubCategory.AUTO_REPLY_CONNECT: MainCategory.AUTOMATE_REPLY,
    SubCategory.EMPTY_REPLY: MainCategory.AUTOMATE_REPLY,
    SubCategory.HARD_BOUNCE: MainCategory.AUTOMATE_REPLY,
}


class TaskPriority(str, Enum):
    """HubSpot task priority levels."""

    HIGHEST = "highest"  # Immediate action required (< 12 hours)
    HIGH = "high"  # Same day action
    MEDIUM = "medium"  # Within 48 hours
    LOW = "low"  # Within 1 week


class ValidationStatus(str, Enum):
    """Lead validation status."""

    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"
    MANUAL_REVIEW = "manual_review"


class TaskStatus(str, Enum):
    """Task sync status."""

    PENDING = "pending"
    SYNCED = "synced"
    COMPLETED = "completed"
    FAILED = "failed"


class WebhookSource(str, Enum):
    """Webhook event sources."""

    SMARTLEAD = "smartlead"
    CONNECTSAFELY = "connectsafely"
    HEYREACH = "heyreach"


class LeadSource(str, Enum):
    """Lead data sources."""

    APOLLO = "apollo"
    LINKEDIN_NAVIGATOR = "linkedin_navigator"
    MANUAL = "manual"


class LinkedInMessageStatus(str, Enum):
    """LinkedIn message approval status."""

    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    SENT = "sent"
    FAILED = "failed"


class LinkedInMessageType(str, Enum):
    """LinkedIn message types."""

    CONNECTION_REQUEST = "connection_request"
    DIRECT_MESSAGE = "direct_message"


# Re-engagement timelines (in days) by subcategory
# Based on Requirements.md section 3.6.1:
# - None = no automatic re-engagement (immediate follow-up or special handling)
# - Special values:
#   - "prospect_defined" for WRONG_TIMING (timing extracted from reply)
#   - NOT_INTERESTED gets 90 days, but 120 days if NPS survey was sent
RE_ENGAGEMENT_DAYS: dict[SubCategory, int | None] = {
    # Interested - mostly no re-engagement (immediate follow-up)
    SubCategory.READY_TO_CHAT_PHONE: None,
    SubCategory.INTRIGUED: None,
    SubCategory.READY_TO_CHAT_OPEN: None,
    SubCategory.CONNECT_WITH_ANOTHER: None,
    SubCategory.MISUNDERSTOOD_INTERESTED: None,
    SubCategory.LONG_TERM_FOLLOWUP: 90,  # 90 days per requirements
    SubCategory.PROSPECT_PITCHING: 180,  # 180 days per requirements
    # Positive Signals - no re-engagement (immediate follow-up)
    SubCategory.REFERRAL: None,
    SubCategory.COMPETITOR_MENTION: None,
    SubCategory.BUDGET_CONFIRMED: None,
    SubCategory.AUTHORITY_CONFIRMED: None,
    # Not Interested
    SubCategory.MISTAKE_WRONG_COMPANY: 30,  # 30 days - wrong contact details
    SubCategory.NOT_INTERESTED: 90,  # 90 days (or 120 days if NPS sent - handled by scheduler service)
    SubCategory.SELF_DISQUALIFY: 60,  # 60 days per requirements
    SubCategory.MISUNDERSTOOD_NOT_INTERESTED: None,
    SubCategory.UNSUBSCRIBE: None,  # Permanent suppression - never re-engage
    # Negative Signals
    SubCategory.HAPPY_WITH_COMPETITOR: 180,  # 180 days per requirements
    SubCategory.RECENT_PURCHASE: 365,  # 365 days per requirements
    SubCategory.WRONG_TIMING: None,  # Prospect-defined timing - extracted from reply
    # Automate Reply
    SubCategory.OUT_OF_OFFICE: None,
    SubCategory.NO_LONGER_WORKS_HERE: 30,  # Research new contact
    SubCategory.AUTO_ACKNOWLEDGE: None,
    SubCategory.AUTO_FORWARD: None,
    SubCategory.AUTO_REPLY_CONNECT: None,
    SubCategory.EMPTY_REPLY: None,
    SubCategory.HARD_BOUNCE: None,  # Permanent suppression - email invalid
}

# Extended re-engagement for NPS survey completion
# When NPS survey is sent for NOT_INTERESTED, use 120 days instead of 90
RE_ENGAGEMENT_DAYS_WITH_NPS = 120


# Task types by subcategory
TASK_TYPES: dict[SubCategory, list[tuple[str, TaskPriority]]] = {
    # Interested
    SubCategory.READY_TO_CHAT_PHONE: [
        ("Review Interested Reply", TaskPriority.HIGH),
        ("LinkedIn Connection Request and DM", TaskPriority.HIGH),
        ("Send appointment suggestion", TaskPriority.HIGH),
    ],
    SubCategory.INTRIGUED: [
        ("Review Interested Reply", TaskPriority.HIGH),
        ("LinkedIn Connection Request and DM", TaskPriority.HIGH),
    ],
    SubCategory.READY_TO_CHAT_OPEN: [
        ("Review Interested Reply", TaskPriority.HIGH),
        ("LinkedIn Connection Request and DM", TaskPriority.HIGH),
        ("Send appointment suggestion", TaskPriority.HIGH),
    ],
    SubCategory.CONNECT_WITH_ANOTHER: [
        ("Internal Colleague Assignment", TaskPriority.HIGH),
    ],
    SubCategory.MISUNDERSTOOD_INTERESTED: [
        ("Clarify Product Misunderstanding", TaskPriority.HIGH),
    ],
    SubCategory.LONG_TERM_FOLLOWUP: [
        ("Prepare 90-Day Nurture Content", TaskPriority.LOW),
    ],
    SubCategory.PROSPECT_PITCHING: [
        ("Prepare 90-Day Nurture Content", TaskPriority.LOW),
    ],
    # Positive Signals
    SubCategory.REFERRAL: [
        ("Create Referral Contact Record", TaskPriority.HIGHEST),
        ("Follow-up Referral Immediately", TaskPriority.HIGHEST),
    ],
    SubCategory.COMPETITOR_MENTION: [
        ("Send Competitor Battle Card", TaskPriority.HIGH),
    ],
    SubCategory.BUDGET_CONFIRMED: [
        ("Book Discovery Call", TaskPriority.HIGH),
    ],
    SubCategory.AUTHORITY_CONFIRMED: [
        ("Book Discovery Call", TaskPriority.HIGH),
    ],
    # Not Interested
    SubCategory.MISTAKE_WRONG_COMPANY: [
        ("Apollo Research Correct Contact", TaskPriority.LOW),
    ],
    SubCategory.NOT_INTERESTED: [
        ("Send NPS Feedback Survey", TaskPriority.LOW),
        ("Schedule 90-Day Nurture Email", TaskPriority.LOW),
    ],
    SubCategory.SELF_DISQUALIFY: [
        ("Schedule 90-Day Nurture Email", TaskPriority.LOW),
    ],
    SubCategory.MISUNDERSTOOD_NOT_INTERESTED: [
        ("Clarify Product Misunderstanding", TaskPriority.HIGH),
    ],
    SubCategory.UNSUBSCRIBE: [
        ("Permanent Email Suppression", TaskPriority.LOW),
    ],
    # Negative Signals
    SubCategory.HAPPY_WITH_COMPETITOR: [
        ("Schedule 180-Day Re-engagement Review", TaskPriority.LOW),
    ],
    SubCategory.RECENT_PURCHASE: [
        ("Track Contract Renewal Date", TaskPriority.LOW),
    ],
    SubCategory.WRONG_TIMING: [
        ("Set Prospect-Defined Follow-up Date", TaskPriority.MEDIUM),
    ],
    # Automate Reply
    SubCategory.NO_LONGER_WORKS_HERE: [
        ("Research Current Contact", TaskPriority.LOW),
    ],
    SubCategory.AUTO_FORWARD: [
        ("Document Forward Recipient", TaskPriority.LOW),
    ],
    SubCategory.HARD_BOUNCE: [
        ("Permanent Email Suppression", TaskPriority.LOW),
    ],
}

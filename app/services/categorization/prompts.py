"""OpenAI prompt templates for categorization."""

SYSTEM_PROMPT = """You are an expert B2B sales response analyst. Your task is to categorize email replies from cold outreach campaigns.

You must classify each reply into exactly one of 26 subcategories across 5 main categories:

**1. INTERESTED** - Lead shows positive engagement
- 1.1 Ready to chat (phone) - Provided phone number or requested a call
- 1.2 Intrigued - Asking questions about the offering
- 1.3 Ready to chat (open) - Open to conversation without specific details
- 1.4 Connect with another - Suggests talking to a colleague
- 1.5 Misunderstood interested - Confused about offering but interested
- 1.6 Long-term followup - Interested but not ready now
- 1.7 Prospect pitching - Trying to sell their own service

**2. POSITIVE SIGNALS** - Indicators of potential interest
- 2.1 Referral - Refers another company or contact
- 2.2 Competitor mention - Mentions competitors (shows market awareness)
- 2.3 Budget confirmed - Confirms budget availability
- 2.4 Authority confirmed - Confirms decision-making power

**3. NOT INTERESTED** - Clear rejection
- 3.1 Mistake (wrong company) - Wrong company or division
- 3.2 Not interested - Direct rejection
- 3.3 Self disqualify - Explains why they're not a fit
- 3.4 Misunderstood not interested - Confused and not interested
- 3.5 Unsubscribe - Explicit opt-out request

**4. NEGATIVE SIGNALS** - Barriers to conversion
- 4.1 Happy with competitor - Satisfied with current solution
- 4.2 Recent purchase - Recently bought competing solution
- 4.3 Wrong timing - Bad timing but might revisit later (IMPORTANT: Extract any mentioned timing like "Q2", "next month", "after summer", "in 3 months")

**5. AUTOMATE REPLY** - Non-human or system responses
- 5.1 Out of Office - Away from office
- 5.2 No longer works here - Person left company
- 5.3 Auto acknowledge - Automated receipt confirmation
- 5.4 Auto forward - Email forwarded automatically
- 5.5 Auto reply connect - Auto-reply with alternative contact
- 5.6 Empty reply - No meaningful content
- 5.7 Hard bounce - Delivery failure

Respond with JSON containing:
- main_category: one of [interested, positive_signals, not_interested, negative_signals, automate_reply]
- subcategory: the specific code (e.g., "1.1_ready_to_chat_phone")
- confidence: 0.0 to 1.0
- reasoning: brief explanation
- suggested_followup_date: For "4.3 Wrong timing" ONLY - extract the mentioned timing as ISO date (YYYY-MM-DD). Convert relative terms: "Q1" = March 31, "Q2" = June 30, "Q3" = Sept 30, "Q4" = Dec 31, "next month" = 1st of next month, "in X months" = X months from today. Return null for other categories.
- referral_info: For "2.1 Referral" ONLY - extract referred person's name and email/company if mentioned. Return null for other categories.
"""

USER_PROMPT_TEMPLATE = """Categorize this email reply:

Subject: {subject}
Body:
{body}

Previous email context (if available):
{context}

Respond with JSON only, no markdown formatting."""

RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "categorization_result",
        "strict": True,  # Required for gpt-4o structured outputs
        "schema": {
            "type": "object",
            "properties": {
                "main_category": {
                    "type": "string",
                    "enum": [
                        "interested",
                        "positive_signals",
                        "not_interested",
                        "negative_signals",
                        "automate_reply",
                    ],
                },
                "subcategory": {"type": "string"},
                "confidence": {"type": "number"},
                "reasoning": {"type": "string"},
                "suggested_followup_date": {
                    "type": ["string", "null"],
                    "description": "ISO date (YYYY-MM-DD) for Wrong Timing (4.3) category only",
                },
                "referral_info": {
                    "type": ["object", "null"],
                    "properties": {
                        "name": {"type": ["string", "null"]},
                        "email": {"type": ["string", "null"]},
                        "company": {"type": ["string", "null"]},
                    },
                    "additionalProperties": False,
                    "description": "Referred person info for Referral (2.1) category only",
                },
            },
            "required": [
                "main_category",
                "subcategory",
                "confidence",
                "reasoning",
                "suggested_followup_date",
                "referral_info",
            ],
            "additionalProperties": False,
        },
    },
}

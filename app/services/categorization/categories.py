"""Category definitions and metadata."""

from dataclasses import dataclass

from app.core.constants import MainCategory, SubCategory


@dataclass
class CategoryInfo:
    """Information about a category."""

    code: str
    name: str
    description: str
    main_category: MainCategory
    examples: list[str]


# Detailed category information for prompts and UI
CATEGORY_INFO: dict[SubCategory, CategoryInfo] = {
    # Interested (1.x)
    SubCategory.READY_TO_CHAT_PHONE: CategoryInfo(
        code="1.1",
        name="Ready to Chat (Phone)",
        description="Lead has provided phone number or explicitly requested a call",
        main_category=MainCategory.INTERESTED,
        examples=[
            "Here's my number: 555-1234",
            "Give me a call at...",
            "Yes, let's schedule a call",
        ],
    ),
    SubCategory.INTRIGUED: CategoryInfo(
        code="1.2",
        name="Intrigued",
        description="Lead is asking questions about the product/service",
        main_category=MainCategory.INTERESTED,
        examples=[
            "How does your service work?",
            "What are your pricing tiers?",
            "Can you tell me more about...",
        ],
    ),
    SubCategory.READY_TO_CHAT_OPEN: CategoryInfo(
        code="1.3",
        name="Ready to Chat (Open)",
        description="Lead is open to a conversation but hasn't provided details",
        main_category=MainCategory.INTERESTED,
        examples=[
            "Sure, let's talk",
            "I'm interested in learning more",
            "What did you have in mind?",
        ],
    ),
    SubCategory.CONNECT_WITH_ANOTHER: CategoryInfo(
        code="1.4",
        name="Connect with Another Person",
        description="Lead suggests connecting with a colleague or different department",
        main_category=MainCategory.INTERESTED,
        examples=[
            "You should talk to our VP of...",
            "Let me connect you with...",
            "I'm not the right person, but...",
        ],
    ),
    SubCategory.MISUNDERSTOOD_INTERESTED: CategoryInfo(
        code="1.5",
        name="Misunderstood (Interested)",
        description="Lead misunderstood the offering but shows interest",
        main_category=MainCategory.INTERESTED,
        examples=[
            "Are you offering X? If so, I'm interested",
            "I thought this was about...",
        ],
    ),
    SubCategory.LONG_TERM_FOLLOWUP: CategoryInfo(
        code="1.6",
        name="Long-term Follow-up",
        description="Lead is interested but not ready now, follow up later",
        main_category=MainCategory.INTERESTED,
        examples=[
            "Check back with me in Q3",
            "We're not ready yet, but keep us in mind",
            "Maybe next year",
        ],
    ),
    SubCategory.PROSPECT_PITCHING: CategoryInfo(
        code="1.7",
        name="Prospect Pitching Own Service",
        description="Lead tries to sell their own service in response",
        main_category=MainCategory.INTERESTED,
        examples=[
            "Actually, I think we can help YOU",
            "We offer a similar service...",
        ],
    ),
    # Positive Signals (2.x)
    SubCategory.REFERRAL: CategoryInfo(
        code="2.1",
        name="Referral",
        description="Lead refers another company or contact",
        main_category=MainCategory.POSITIVE_SIGNALS,
        examples=[
            "You should also reach out to...",
            "My friend at XYZ Company might be interested",
        ],
    ),
    SubCategory.COMPETITOR_MENTION: CategoryInfo(
        code="2.2",
        name="Competitor Mention",
        description="Lead mentions a competitor, showing market awareness",
        main_category=MainCategory.POSITIVE_SIGNALS,
        examples=[
            "How do you compare to Competitor X?",
            "We're currently using...",
        ],
    ),
    SubCategory.BUDGET_CONFIRMED: CategoryInfo(
        code="2.3",
        name="Budget Confirmed",
        description="Lead confirms they have budget available",
        main_category=MainCategory.POSITIVE_SIGNALS,
        examples=[
            "We have budget for this",
            "What's your pricing?",
        ],
    ),
    SubCategory.AUTHORITY_CONFIRMED: CategoryInfo(
        code="2.4",
        name="Authority Confirmed",
        description="Lead confirms decision-making authority",
        main_category=MainCategory.POSITIVE_SIGNALS,
        examples=[
            "I'm the one who makes these decisions",
            "I'll need to get buy-in from...",
        ],
    ),
    # Not Interested (3.x)
    SubCategory.MISTAKE_WRONG_COMPANY: CategoryInfo(
        code="3.1",
        name="Wrong Company/Branch",
        description="Email reached the wrong company or division",
        main_category=MainCategory.NOT_INTERESTED,
        examples=[
            "You have the wrong company",
            "This is the wrong branch",
        ],
    ),
    SubCategory.NOT_INTERESTED: CategoryInfo(
        code="3.2",
        name="Not Interested",
        description="Direct rejection without specific reason",
        main_category=MainCategory.NOT_INTERESTED,
        examples=[
            "Not interested",
            "No thanks",
            "Please remove me from your list",
        ],
    ),
    SubCategory.SELF_DISQUALIFY: CategoryInfo(
        code="3.3",
        name="Self-disqualify",
        description="Lead explains why they're not a fit",
        main_category=MainCategory.NOT_INTERESTED,
        examples=[
            "We're too small for this",
            "We don't do X",
            "We're shutting down",
        ],
    ),
    SubCategory.MISUNDERSTOOD_NOT_INTERESTED: CategoryInfo(
        code="3.4",
        name="Misunderstood (Not Interested)",
        description="Lead misunderstood offering and is not interested",
        main_category=MainCategory.NOT_INTERESTED,
        examples=[
            "If this is about X, I'm not interested",
        ],
    ),
    SubCategory.UNSUBSCRIBE: CategoryInfo(
        code="3.5",
        name="Unsubscribe",
        description="Explicit unsubscribe or do-not-contact request",
        main_category=MainCategory.NOT_INTERESTED,
        examples=[
            "Unsubscribe",
            "Stop emailing me",
            "Remove me from your list",
        ],
    ),
    # Negative Signals (4.x)
    SubCategory.HAPPY_WITH_COMPETITOR: CategoryInfo(
        code="4.1",
        name="Happy with Competitor",
        description="Lead is satisfied with current solution",
        main_category=MainCategory.NEGATIVE_SIGNALS,
        examples=[
            "We're happy with our current provider",
            "We already use X and it works well",
        ],
    ),
    SubCategory.RECENT_PURCHASE: CategoryInfo(
        code="4.2",
        name="Recent Purchase",
        description="Lead recently bought a competing solution",
        main_category=MainCategory.NEGATIVE_SIGNALS,
        examples=[
            "We just signed a contract with...",
            "We purchased X last month",
        ],
    ),
    SubCategory.WRONG_TIMING: CategoryInfo(
        code="4.3",
        name="Wrong Timing",
        description="Bad timing but might be interested later",
        main_category=MainCategory.NEGATIVE_SIGNALS,
        examples=[
            "Bad timing, we're in the middle of...",
            "Maybe after our merger",
        ],
    ),
    # Automate Reply (5.x)
    SubCategory.OUT_OF_OFFICE: CategoryInfo(
        code="5.1",
        name="Out of Office",
        description="Auto-reply indicating person is away",
        main_category=MainCategory.AUTOMATE_REPLY,
        examples=[
            "I am currently out of the office",
            "On vacation until...",
        ],
    ),
    SubCategory.NO_LONGER_WORKS_HERE: CategoryInfo(
        code="5.2",
        name="No Longer Works Here",
        description="Person has left the company",
        main_category=MainCategory.AUTOMATE_REPLY,
        examples=[
            "John no longer works here",
            "This person has left the company",
        ],
    ),
    SubCategory.AUTO_ACKNOWLEDGE: CategoryInfo(
        code="5.3",
        name="Auto Acknowledge",
        description="Automated acknowledgment without human content",
        main_category=MainCategory.AUTOMATE_REPLY,
        examples=[
            "Thank you for your email",
            "Your message has been received",
        ],
    ),
    SubCategory.AUTO_FORWARD: CategoryInfo(
        code="5.4",
        name="Auto Forward",
        description="Email was automatically forwarded",
        main_category=MainCategory.AUTOMATE_REPLY,
        examples=[
            "Your email has been forwarded to...",
            "This mailbox is monitored by...",
        ],
    ),
    SubCategory.AUTO_REPLY_CONNECT: CategoryInfo(
        code="5.5",
        name="Auto Reply Connect",
        description="Auto-reply suggesting another contact",
        main_category=MainCategory.AUTOMATE_REPLY,
        examples=[
            "For inquiries, please contact...",
            "Please email sales@...",
        ],
    ),
    SubCategory.EMPTY_REPLY: CategoryInfo(
        code="5.6",
        name="Empty Reply",
        description="Reply with no meaningful content",
        main_category=MainCategory.AUTOMATE_REPLY,
        examples=[
            "(empty email body)",
            ".",
        ],
    ),
    SubCategory.HARD_BOUNCE: CategoryInfo(
        code="5.7",
        name="Hard Bounce",
        description="Email delivery failed permanently",
        main_category=MainCategory.AUTOMATE_REPLY,
        examples=[
            "Delivery Status Notification (Failure)",
            "Address not found",
        ],
    ),
}

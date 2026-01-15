"""MS Teams notification message formatting."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.core.constants import TaskPriority


@dataclass
class NotificationContent:
    """Content for MS Teams notification."""

    title: str
    priority: TaskPriority
    lead_name: str
    company_name: str
    email: str
    phone: str | None
    task_description: str
    hubspot_task_url: str | None
    draft_message: str | None
    meeting_agenda: str | None
    suggested_time_slots: list[str] = field(default_factory=list)


def generate_suggested_time_slots(
    num_slots: int = 3,
    start_hour: int = 9,
    end_hour: int = 17,
    prospect_timezone: str | None = None,
) -> list[str]:
    """
    Generate suggested meeting time slots for the next few business days.

    Args:
        num_slots: Number of slots to generate
        start_hour: Business day start (default 9 AM)
        end_hour: Business day end (default 5 PM)
        prospect_timezone: IANA timezone string (e.g., "America/New_York", "Europe/London")
                          If provided, times will be shown in the prospect's timezone

    Returns:
        List of formatted time slot strings
    """
    slots = []

    # Use prospect's timezone if provided, otherwise UTC
    try:
        tz = ZoneInfo(prospect_timezone) if prospect_timezone else timezone.utc
    except Exception:
        tz = timezone.utc  # Fallback to UTC if invalid timezone

    now = datetime.now(tz)

    # Start from next business day if after business hours
    current = now
    if current.hour >= end_hour:
        current += timedelta(days=1)
        current = current.replace(hour=start_hour, minute=0)
    elif current.hour < start_hour:
        current = current.replace(hour=start_hour, minute=0)
    else:
        # Round up to next hour
        current = current.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

    attempts = 0
    max_attempts = 10  # Prevent infinite loop

    while len(slots) < num_slots and attempts < max_attempts:
        attempts += 1

        # Skip weekends
        if current.weekday() >= 5:  # Saturday=5, Sunday=6
            current += timedelta(days=1)
            current = current.replace(hour=start_hour, minute=0)
            continue

        # Check if within business hours
        if current.hour < start_hour:
            current = current.replace(hour=start_hour, minute=0)
        elif current.hour >= end_hour:
            current += timedelta(days=1)
            current = current.replace(hour=start_hour, minute=0)
            continue

        # Format slot
        slot_str = current.strftime("%A, %B %d at %I:%M %p %Z")
        slots.append(slot_str)

        # Move to next slot (2 hours later or next day)
        current += timedelta(hours=2)

    return slots


class NotificationFormatter:
    """Formatter for MS Teams adaptive cards."""

    # Priority colors for Teams cards
    PRIORITY_COLORS: dict[TaskPriority, str] = {
        TaskPriority.HIGHEST: "attention",  # Red
        TaskPriority.HIGH: "warning",  # Yellow
        TaskPriority.MEDIUM: "accent",  # Blue
        TaskPriority.LOW: "default",  # Gray
    }

    def format_adaptive_card(self, content: NotificationContent) -> dict:
        """
        Format notification as MS Teams Adaptive Card.

        Args:
            content: Notification content

        Returns:
            Adaptive Card JSON structure
        """
        card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": None,
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": self._build_card_body(content),
                        "actions": self._build_card_actions(content),
                    },
                }
            ],
        }
        return card

    def _build_card_body(self, content: NotificationContent) -> list[dict]:
        """Build adaptive card body elements."""
        color = self.PRIORITY_COLORS.get(content.priority, "default")

        body = [
            # Header with priority badge
            {
                "type": "ColumnSet",
                "columns": [
                    {
                        "type": "Column",
                        "width": "auto",
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": f"[{content.priority.value.upper()}]",
                                "weight": "bolder",
                                "color": color,
                            }
                        ],
                    },
                    {
                        "type": "Column",
                        "width": "stretch",
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": content.title,
                                "weight": "bolder",
                                "size": "medium",
                                "wrap": True,
                            }
                        ],
                    },
                ],
            },
            # Lead info
            {
                "type": "FactSet",
                "facts": [
                    {"title": "Lead", "value": content.lead_name},
                    {"title": "Company", "value": content.company_name},
                    {"title": "Email", "value": content.email},
                ],
            },
        ]

        # Add phone if available
        if content.phone:
            body[-1]["facts"].append({"title": "Phone", "value": content.phone})

        # Task description
        body.append(
            {
                "type": "TextBlock",
                "text": f"**Required Action:** {content.task_description}",
                "wrap": True,
            }
        )

        # Draft message if available
        if content.draft_message:
            body.append(
                {
                    "type": "TextBlock",
                    "text": "**Draft Message:**",
                    "weight": "bolder",
                }
            )
            body.append(
                {
                    "type": "TextBlock",
                    "text": content.draft_message,
                    "wrap": True,
                    "isSubtle": True,
                }
            )

        # Meeting agenda if available
        if content.meeting_agenda:
            body.append(
                {
                    "type": "TextBlock",
                    "text": "**Meeting Agenda:**",
                    "weight": "bolder",
                }
            )
            body.append(
                {
                    "type": "TextBlock",
                    "text": content.meeting_agenda,
                    "wrap": True,
                    "isSubtle": True,
                }
            )

        # Suggested time slots if available
        if content.suggested_time_slots:
            body.append(
                {
                    "type": "TextBlock",
                    "text": "**Available Times:**",
                    "weight": "bolder",
                    "spacing": "medium",
                }
            )
            # Format as bullet list
            slots_text = "\n".join(f"• {slot}" for slot in content.suggested_time_slots)
            body.append(
                {
                    "type": "TextBlock",
                    "text": slots_text,
                    "wrap": True,
                    "isSubtle": True,
                }
            )

        return body

    def _build_card_actions(self, content: NotificationContent) -> list[dict]:
        """Build adaptive card action buttons."""
        actions = []

        if content.hubspot_task_url:
            actions.append(
                {
                    "type": "Action.OpenUrl",
                    "title": "View in HubSpot",
                    "url": content.hubspot_task_url,
                }
            )

        return actions

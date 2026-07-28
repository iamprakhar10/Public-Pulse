from enum import Enum


class ComplaintCategory(str, Enum):
    """
    Fixed complaint categories supported by Public Pulse.

    Using an Enum keeps the database values consistent and helps
    with authority matching and dashboard aggregation.
    """

    ROAD = "road"
    WATER = "water"
    ELECTRICITY = "electricity"
    SANITATION = "sanitation"
    POLICE = "police"
    GOVERNMENT_SCHOOL = "government_school"
    WOMEN_SAFETY = "women_safety"
    CHILD_LABOUR = "child_labour"
    OVERPRICING = "overpricing"
    OTHER = "other"


class ComplaintStatus(str, Enum):
    """
    Allowed stages in a complaint's lifecycle.

    Using an Enum prevents random status strings such as
    "done", "finished", or "complete" from entering the database
    """

    DRAFT = 'draft'
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    SENT = 'sent'
    UNRESOLVED = "unresolved"
    PARTIALLY_RESOLVED = "partially_resolved"
    RESOLVED = "resolved"


class MessageRole(str, Enum):
    """
    Identifies who created a conversation message
    """
    USER = 'user'
    ASSISTANT = 'assistant'
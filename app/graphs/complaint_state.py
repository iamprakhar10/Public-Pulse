from typing import TypedDict

from app.constants.complaint import ComplaintCategory



class ComplaintGraphState(TypedDict, total=False):
    """
    State/Data that will be passed from one node to others in the 
    Langgraph graph

    total=False means fields may be added gradually as the graph processes
    the complaint
    """

    # Identifies the complaint and it's owner
    complaint_id: int
    user_id: int

    # Conversation converted into LLM-compatible dictionaries.
    messages: list[dict[str, str]]
    
    # Structured complaint information extracted by llm
    summary: str
    category: ComplaintCategory | None
    city: str | None
    area: str | None
    pincode: str | None

    city_id: int | None
    authority_id: int | None

    # Controls conditional graph routing
    is_complete: bool
    next_question: str | None

    # Email drafting information
    email_subject : str | None
    email_body : str | None

    # Used when a node can't complete it's work 
    error : str | None



# Avoiding  this: ORM objects stored in graph state
# complaint: Complaint
# authority: Authority
# db: Session

# Graph state may later be checkpointed. SQLAlchemy sessions and
# ORM objects are not suitable persistent graph-state values. 
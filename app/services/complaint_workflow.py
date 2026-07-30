"""
Receive a new user message
        ↓
Store it in complaint_messages
        ↓
Load the complete conversation
        ↓
Convert ORM messages to dictionaries
        ↓
Call analyse_complaint_conversation()
        ↓
Update Complaint structured fields
        ↓
Store next_question as an assistant message
        ↓
Return the updated complaint conversation
"""

from sqlalchemy.orm import Session

from app.constants.complaint import (
    MessageRole, 
    ComplaintStatus,
)
from app.database.complaint_crud import (
    add_complaint_message,
    get_user_complaint,
    update_complaint_structured_data,
)

from app.database.models import Complaint, City, Authority
from app.schemas.complaint import ComplaintStructuredUpdate
from app.services.complaint_ai import analyse_complaint_conversation

from app.services.location_resolver import resolve_city

from app.database.authority_crud import get_authority_for_complaint

def convert_messages_for_llm(
        complaint: Complaint,
) -> list[dict[str,str]]:
    """
    Convert SQLAlchemy message objects into dictionary format
    as expected by the complaint AI service
    """

    return [
        {
            'role': message.role.value,
            'content': message.content,
        }
        for message in complaint.messages
    ]




def resolve_analysis_city(
        db:Session,
        city_name: str|None,
) -> City|None:
    """
    Resolve the city text returned by the LLM to a canonical City row.

    Returns:
        City:
            When the extracted city matches a supported canonical city
            name or one of its registered aliases.

        None:
            When the LLM has not extracted a city yet.

    Raises:
        ValueError:
            When the LLM returned a city, but it is unsupported,
            ambiguous, or cannot be resolved.
    """

    if city_name is None or not city_name.strip():
        return None

    return resolve_city(
        db=db,
        city_name=city_name,
    )




def process_user_complaint_message(
       db: Session,
       complaint_id: int,
       user_id: int, 
       content: str,
) -> Complaint:
    """
    Storing a new user message and running the complaint AI workflow

    1. Verify complaint ownership
    2. store the user message
    3. Reload the complaete conversatinn
    4. Update structured complaint fields
    5. Update structured complaint fields
    6. Store the assistant's followup question
    7. Return the updatesd conversation
    """
    complaint = get_user_complaint(
        db=db,
        complaint_id=complaint_id,
        user_id=user_id,
    )

    if complaint is None:
        raise ValueError('Complaint not found.')

    if complaint.status != ComplaintStatus.DRAFT:
        raise ValueError(
        "This complaint is no longer accepting conversation messages."
    )

    add_complaint_message(
        db=db,
        complaint_id=complaint_id,
        content=content,
        role=MessageRole.USER,
    )

    # Now we will reload the complaint so that it contains the
    # inserted message 
    complaint = get_user_complaint(
        db=db,
        complaint_id=complaint_id,
        user_id=user_id,
    )

    if complaint is None:
        raise ValueError("Complaint couldn't be reloaded")

    messages = convert_messages_for_llm(complaint)

    analysis = analyse_complaint_conversation(
        messages=messages,
    )


    # The LLM returns city as text, such as:
    # "Jabalpur", "JBP", or "Jabalpur City".
    #
    # Our resolver converts that text into a trusted City database row.
    resolved_city : City | None=None
    city_resolution_failed = False

    try:
        resolved_city = resolve_analysis_city(
            db=db,
            city_name=analysis.city,
        )

    except ValueError:
        # A city was extracted, but it could not be matched to one of
        # the supported cities.
        #
        # We do not trust the raw LLM output and we do not allow the
        # complaint to become complete.
        city_resolution_failed = True


    resolved_authority : Authority | None = None

    if (
        resolved_city is not None
        and analysis.pincode is not None
        and analysis.category is not None
    ):
        resolved_authority = get_authority_for_complaint(
            db=db,
            city_id=resolved_city.id,
            pincode=analysis.pincode,
            category=analysis.category,
        )


    # Store only the canonical city name.
    #
    # Example:
    # LLM output: "JBP"
    # Stored value: "Jabalpur"
    canonical_city_name = (
        resolved_city.name
        if resolved_city is not None
        else None
    )

    # We will add only those fields which are present in Complaint-
    # model/table 
    structured_update = ComplaintStructuredUpdate(
        summary=analysis.summary,
        category=analysis.category,
        city=canonical_city_name,
        area=analysis.area,
        pincode=analysis.pincode,
    )

    update_complaint_structured_data(
        db=db,
        complaint=complaint,
        update_data=structured_update,
    )

    # Store the canonical foreign key when resolution succeeds.
    if resolved_city is not None:
        complaint.city_id = resolved_city.id
    else:
        complaint.city_id = None



    # The complaint is truly complete only when:
    # 1. The LLM says all required details are available.
    # 2. The city has been resolved to a supported City row.
    is_truly_complete = (
        analysis.is_complete
        and resolved_city is not None
        and resolved_authority is not None
    )

    if is_truly_complete:
        complaint.status = ComplaintStatus.AWAITING_APPROVAL
    else:
        complaint.status = ComplaintStatus.DRAFT
    db.commit()
    db.refresh(complaint)


    # Decide which clarification question should be stored.
    next_question = analysis.next_question
    if city_resolution_failed:
        next_question = (
            "I could not identify the city reliably. "
            "Which city is this issue located in?"
        )

    elif (
        resolved_city is None 
        and not next_question
        and resolved_authority is None
    ):
        next_question = (
            "I could not verify that pincode for this location. "
            "What is the correct pincode?"
        )

    elif resolve_city is None and not next_question:
        next_question = (
        "Which city is this issue located in?"
    )

        
    # Store a follow-up question only when the complaint is incomplete.
    if not is_truly_complete and next_question is not None:
        add_complaint_message(
            db=db,
            complaint_id=complaint_id,
            content=next_question,
            role=MessageRole.ASSISTANT,
        )

    # Reload once more so the returned complaint includes the latest
    # assistant message and all updated fields.
    updated_complaint = get_user_complaint(
        db=db,
        complaint_id=complaint_id,
        user_id=user_id,
    )

    if updated_complaint is None:
        raise ValueError(
            "Updated complaint could not be reloaded."
        )

    return updated_complaint


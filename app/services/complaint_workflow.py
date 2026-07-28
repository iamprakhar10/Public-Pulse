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

from app.constants.complaint import MessageRole
from app.database.complaint_crud import (
    add_complaint_message,
    get_user_complaint,
    update_complaint_structured_data,
)

from app.database.models import Complaint
from app.schemas.complaint import ComplaintStructuredUpdate
from app.services.complaint_ai import analyse_complaint_conversation



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

    # We will add only those fields which are present in Complaint-
    # model/table 
    structured_update = ComplaintStructuredUpdate(
        summary=analysis.summary,
        category=analysis.category,
        city=analysis.city,
        area=analysis.area,
        pincode=analysis.pincode,
    )

    update_complaint_structured_data(
        db=db,
        complaint=complaint,
        update_data=structured_update,
    )

    if analysis.next_question is not None:
        add_complaint_message(
            db=db,
            complaint_id=complaint_id,
            content=analysis.next_question,
            role=MessageRole.ASSISTANT,
        )
    updated_complaint = get_user_complaint(
        db=db,
        complaint_id=complaint_id,
        user_id=user_id,
    )    

    if updated_complaint is None:
        raise ValueError(
            "Updated complaint couldn't be reloaded"
        )

    return updated_complaint





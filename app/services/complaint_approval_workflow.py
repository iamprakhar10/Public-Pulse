from sqlalchemy.orm import Session

from app.constants.complaint import ComplaintStatus
from app.database.complaint_crud import(
    approve_complaint_email_draft,
    get_user_complaint,
    update_complaint_email_draft,
)
from app.database.models import Complaint, User
from app.schemas.complaint import ComplaintEmailDraftUpdate

def edit_complaint_email_draft(
        db:Session,
        complaint_id: int,
        user:User,
        draft_data: ComplaintEmailDraftUpdate,
) -> Complaint:
    """
    Update the saved email draft after checking ownership and
    complaint status
    """

    complaint = get_user_complaint(
        db=db,
        complaint_id=complaint_id,
        user_id=user.id,
    )

    if complaint is None:
        raise ValueError('Complaint not found.')

    if complaint.status != ComplaintStatus.AWAITING_APPROVAL:
        raise ValueError(
            'This complaint cannot be currently edited'
        )
    if (complaint.email_subject is None 
        or complaint.email_body is None):
        raise ValueError(
            "Generate an email draft before editing it"
        )
    return update_complaint_email_draft(
        db=db,
        complaint=complaint,
        subject=draft_data.subject,
        body=draft_data.body,
    )

def approve_complaint_draft(
        db:Session,
        complaint_id:int,
        user:User,
) -> Complaint:
    """
    Explicitly approving the current saved email draft
    """

    complaint = get_user_complaint(
        db=db,
        complaint_id=complaint_id,
        user_id=user.id,
    )
    if complaint is None:
            raise ValueError('Complaint not found.')
    
    if complaint.status != ComplaintStatus.AWAITING_APPROVAL:
        raise ValueError(
            'This complaint is not waiting Approval'
        )
    return approve_complaint_email_draft(
         db=db,
         complaint=complaint,
    )
from sqlalchemy.orm import Session

from app.constants.complaint import ComplaintStatus
from app.database.complaint_crud import (
    get_user_complaint,
    save_complaint_email_draft,
)
from app.database.models import Complaint, User
from app.services.complaint_email_ai import (
    generate_complaint_email_draft,
)

def create_complaint_email_draft(
        db: Session,
        complaint_id:int,
        user: User,
) -> Complaint:
    """
    Generate and save email draft for a complete complaint

    - Confirm complaint ownreship
    - Conirming complaint is ready for review ie AWAITING_APPROVAL
    - Generate the email using complaint & user's name
    - save the generated subject and body
    - return the updated complaint
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
            'The complaint is not ready for email generation'
        )

    draft = generate_complaint_email_draft(
        complaint=complaint,
        user=user,
    )

    return save_complaint_email_draft(
        db=db,
        complaint=complaint,
        subject=draft.subject,
        body=draft.body,
    )
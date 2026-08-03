"""
Logic for sending approved complaint email
"""

from sqlalchemy.orm import Session

from app.constants.complaint import ComplaintStatus
from app.database.complaint_crud import get_user_complaint
from app.database.models import Complaint
from app.services.email_sender import EmailSender



def send_approved_complaint_email(
        db: Session,
        complaint_id: int,
        user_id: int,
        email_sender: EmailSender,
) -> Complaint:
    """
    Send an approved complaint to its matched authority
    get_user_complaint is also called and do the ownership check
    """

    complaint = get_user_complaint(
        db=db,
        complaint_id=complaint_id,
        user_id=user_id
    )

    if complaint is None:
        raise ValueError(
            'Complaint not found'
        )

    if complaint.status != ComplaintStatus.APPROVED:
        raise ValueError(
            "The complaint email must be approved before it can be sent."
        )

    if complaint.authority is None:
        raise ValueError(
            " No authority is assigned to this complaint."
        )

    if not complaint.authority.email:
        raise ValueError(
            "The assigned authority doesn't have their email registered"
        )

    if not complaint.email_subject:
        raise ValueError(
            "The complaint email doesn't have an email subject"
        )

    if not complaint.email_body:
        raise ValueError(
            " The complaint email doesn't have email body"
        )

    email_sender.send_email(
        recipient=complaint.authority.email,
        subject=complaint.email_subject,
        body=complaint.email_body,
    )

    complaint.status = ComplaintStatus.SENT

    db.commit()
    db.refresh(complaint)

    return complaint
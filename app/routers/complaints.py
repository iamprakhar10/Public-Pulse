from fastapi import APIRouter, Depends,HTTPException, status
from sqlalchemy.orm import Session

from app.constants.complaint import MessageRole
from app.database.complaint_crud import(
    add_complaint_message,
    create_complaint,
    get_user_complaint,
    get_user_complaints,
)

from app.database.dependencies import get_current_user, get_db
from app.database.models import User, Complaint
from app.schemas.complaint import (
    ComplaintConversationResponse,
    ComplaintMessageCreate,
    ComplaintResponse,
    ComplaintStart,
    ComplaintMessageResponse,
    ComplaintApprovalResponse,
    ComplaintEmailDraftUpdate,
)

from app.services.complaint_workflow import (
    process_user_complaint_message,
    process_started_complaint,
)
from app.services.complaint_email_workflow import (
    create_complaint_email_draft,
)
from app.services.complaint_approval_workflow import (
    approve_complaint_draft,
    edit_complaint_email_draft
)

from app.services.complaint_send_workflow import (
    send_approved_complaint_email,
)
from app.services.email_sender import (
    ConsoleEmailSender,
    EmailSender,
)




# Grouping all complaint-related endpoints under /complaints
router = APIRouter(
    prefix='/complaints',
    tags=['Complaints'],
)














@router.post(
    "",
    response_model=ComplaintConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_complaint(
    complaint_data:ComplaintStart,
    db:Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ComplaintConversationResponse:
    """
    Creating a complaint, storing it's first message
    And then running Langgraph

    """


    complaint = create_complaint(
        db=db,
        user_id=current_user.id,
        first_message=complaint_data.message,
    )

    return process_started_complaint(
        db=db,
        complaint_id=complaint.id,
        user_id=current_user.id,
    )
    # # Retrieve it again with it's messages loaded
    # created_complaint=get_user_complaint(
    #     db=db,
    #     complaint_id=complaint.id,
    #     user_id=current_user.id,
    # )

    # if created_complaint is None:
    #     raise HTTPException(
    #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #         detail="Complaint was created but couldnot be laoded",
    #     )

    # return created_complaint














@router.get(
    '',
    response_model=list[ComplaintResponse],
)
def list_my_complaints(
    db:Session= Depends(get_db),
    current_user:User = Depends(get_current_user),
):
    """
    This will return all complaints belonging to the 
    authenticated user.

    A user can't list another user's complaint because the user
    ID comes from the validated JWT TOKEN, not from request input
    """

    return get_user_complaints(
        db=db,
        user_id=current_user.id,
    )











@router.get(
    '/{complaint_id}',
    response_model=ComplaintConversationResponse,
)
def get_my_complaint(
    complaint_id:int,
    db:Session = Depends(get_db),
    current_user:User=Depends(get_current_user),
) -> ComplaintConversationResponse:
    """
    Return one complaint together with it's full chat history

    The querry will check both complaint id and authenticated user
    id.
    So that user can only read their own complaint
    """
    complaint = get_user_complaint(
        db=db,
        complaint_id=complaint_id,
        user_id=current_user.id,
    )

    if complaint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )
    return complaint











@router.post(
    '/{complaint_id}/messages',
    response_model=ComplaintConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_user_message(
    complaint_id: int,
    message_data: ComplaintMessageCreate,
    db:Session=Depends(get_db),
    current_user:User = Depends(get_current_user),
) -> ComplaintConversationResponse:
    """
    Adding another user message to an existing complaint
    conversation

    Frontend will only send the content of the user message.
    We in bacvkend assign the role, so the client doesn't
    "accidentally" become AI assistant
    """

    """
    Add a user message and run the full AI complaint workflow.

    The workflow:
    1. Stores the user's message.
    2. Analyses the complete conversation.
    3. Updates structured complaint fields.
    4. Stores the assistant's next question.
    5. Returns the updated complaint conversation.
    """

    try:
        return process_user_complaint_message(
            db=db,
            complaint_id=complaint_id,
            user_id=current_user.id,
            content=message_data.content,
        )

    except ValueError as exc:
        error_message = str(exc)

        if error_message == (
            "This complaint is no longer accepting conversation messages."
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_message,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    # complaint = get_user_complaint(
    #     db=db,
    #     complaint_id=complaint_id,
    #     user_id=current_user.id,
    # )

    # if complaint is None:
    #     raise HTTPException(
    #         status_code=status.HTTP_404_NOT_FOUND,
    #         detail='Complaint not found'
    #     )

    # return add_complaint_message(
    #     db=db,
    #     complaint_id=complaint_id,
    #     content=message_data.content,
    #     role=MessageRole.USER,
    # )












@router.post(
    '/{complaint_id}/email-draft',
    response_model=ComplaintConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_email_draft(
    complaint_id:int,
    db:Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ComplaintConversationResponse:
    """
    Generates and saves a formal email DRAFT for a completed complaint

    The draft email will be stored in the database
    """

    try:
        return create_complaint_email_draft(
            db=db,
            complaint_id=complaint_id,
            user=current_user,
        )

    except ValueError as exc:
        error_message = str(exc)

        if error_message == "Complaint not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_message,
            ) from exc

        raise HTTPException(
            status_code= status.HTTP_409_CONFLICT,
            detail=error_message,
        ) from exc











@router.patch(
    "/{complaint_id}/email-draft",
    response_model=ComplaintConversationResponse,
    status_code=status.HTTP_200_OK,
)
def edit_email_draft(
    complaint_id: int,
    draft_data: ComplaintEmailDraftUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ComplaintConversationResponse:
    """
    Allowing the authenticated user to edit the ai generated
    email draft

    It won't approve or send the email
    """
    try:
        return edit_complaint_email_draft(
            db=db,
            complaint_id=complaint_id,
            user=current_user,
            draft_data=draft_data,
        )
    except ValueError as exc : 
        error_message = str(exc)

        if error_message == "Complaint not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_message,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_message,
        ) from exc










@router.post(
    "/{complaint_id}/approve",
    response_model=ComplaintApprovalResponse,
)
def approve_email_draft(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ComplaintApprovalResponse:
    """
    Explicitly approve the saved email draft

    This won't send the email, only changes the complaint status
    """
    try:
        return approve_complaint_draft(
            db=db,
            complaint_id=complaint_id,
            user=current_user,
        )

    except ValueError as exc:
        error_message = str(exc)

        if error_message == "Complaint not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_message,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_message,
        ) from exc
    






















def get_email_sender() -> EmailSender:
    """
    Dependency function
    Provides the email delivery implementation used by API

    Currently ConsoleEmailSender just prints the email in. terminal

    Later we will replace it
    """

    return ConsoleEmailSender()

@router.post(
    "/{complaint_id}/send",
    response_model=ComplaintConversationResponse,
    status_code=status.HTTP_200_OK,
)
def send_complaint_email(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    email_sender: EmailSender = Depends(get_email_sender),
) -> Complaint:
    """
    Sends an appreoved complaint email to the matched authority

    Current development behaviour:
    - ConsoleEmailSender prints the email in the terminal.
    - After successful delivery, complaint status becomes SENT.

    Later:
    - ConsoleEmailSender will be replaced with GmailEmailSender.
    """

    try:
        return send_approved_complaint_email(
            db=db,
            complaint_id=complaint_id,
            user_id=current_user.id,
            email_sender=email_sender,
        )

    except ValueError as exc:
        error_message = str(exc)
        if error_message.startswith("Complaint not found"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_message,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_message,
        ) from exc
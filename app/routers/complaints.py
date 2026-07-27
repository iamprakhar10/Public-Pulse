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
from app.database.models import User
from app.schemas.complaint import (
    ComplaintConversationResponse,
    ComplaintMessageCreate,
    ComplaintResponse,
    ComplaintStart,
    ComplaintMessageResponse,
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
    Starts a new complaint conversation

    FastAPI
    - Validates the incoming JSON using ComplaintStart(pydantic)
    - Identifies the logged-in user using JWT
    - Create a Complaint row
    - Store the first user message
    - Returns the complaint with its conversation
    """

    complaint = create_complaint(
        db=db,
        user_id=current_user.id,
        first_message=complaint_data.message,
    )

    # Retrieve it again with it's messages loaded
    created_complaint=get_user_complaint(
        db=db,
        complaint_id=complaint.id,
        user_id=current_user.id,
    )

    if created_complaint is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Complaint was created but couldnot be laoded",
        )

    return created_complaint

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
    response_model=ComplaintMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_user_message(
    complaint_id: int,
    message_data: ComplaintMessageCreate,
    db:Session=Depends(get_db),
    current_user:User = Depends(get_current_user),
) -> ComplaintMessageResponse:
    """
    Adding another user message to an existing complaint
    conversation

    Frontend will only send the content of the user message.
    We in bacvkend assign the role, so the client doesn't
    "accidentally" become AI assistant
    """

    complaint = get_user_complaint(
        db=db,
        complaint_id=complaint_id,
        user_id=current_user.id,
    )

    if complaint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Complaint not found'
        )

    return add_complaint_message(
        db=db,
        complaint_id=complaint_id,
        content=message_data.content,
        role=MessageRole.USER,
    )


from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.constants.complaint import (
    ComplaintCategory,
    ComplaintStatus,
    MessageRole,
)

# How a validated 6 digit pincode look like
Pincode = Annotated[
    str,
    StringConstraints(pattern=r'^\d{6}$')
    ]

class ComplaintStart(BaseModel):
    """
    Data required when user starts a new complaint conversation
    Here we only require the user's first message sent to llm. 
    The LLM will collect and extract needed details later on
    """

    message: str = Field(
        min_length=5,
        max_length=2500,
    )


class ComplaintMessageCreate(BaseModel):
    """
    Data sent when user adds another message to an EXISTING COMPLAINT
    CONVERSATION.

    The API won't accept a role because this route will only be used by 
    authenticated user. We will assingn role='user' in the backend

    """
    content: str = Field(
        min_length=1,
        max_length=2500,
    )

class ComplaintMessageResponse(BaseModel):
    """
    This schema is returned to the frontend when displaying the
    complaint chat history
    """

    id: int
    complaint_id: int
    role: MessageRole
    content: str
    created_at: datetime

    #Allows pydantic to read values from SQLAlchemy orm objjescts.
    model_config = ConfigDict(from_attributes=True)


class ComplaintResponse(BaseModel):
    """
    Safe api representation of one complaint case
    or in short show complaint summary schema lol

    Here we are keeping some structured fields as optional as they
    may not have been extracted yet during the conversation
    """

    id: int
    user_id: int
    summary:str | None
    category: ComplaintCategory | None
    city: str|None
    area: str | None
    pincode: str | None
    status: ComplaintStatus
    email_subject: str | None
    email_body: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComplaintConversationResponse(ComplaintResponse):
    """
    Complte complaint reseponse including it's ordered conversation

    Useful if user wants to see an individual complaint i frontend
    """

    messages : list[ComplaintMessageResponse]
    # Here we won't need model_config = ConfigDict(from_attributes=True)
    # even though it is a response schema and it needs it, because it
    # is inheriting from ComplaintResponse and it has it there



class ComplaintStructuredUpdate(BaseModel):
    """
    Structured complaint information extracted from the conversation.

    Initially this will be useful in tests and internal development.
    Later the LLM service will produce these values automatically
    """

    summary: str | None = Field(
        default=None,
        max_length=1255,
    )

    category: ComplaintCategory|None = None

    city: str|None = Field(
        default=None,
        max_length=100,
    )

    area: str | None = Field(
        default=None,
        max_length=150,
    )

    pincode: Pincode| None=None

class ComplaintStatusUpdate(BaseModel):
    """
    Data required to update a complaint's lifecycle status.

    Later, the route will enforce which status changes can be done
    Are they even allowed
    """
    status: ComplaintStatus


class ComplaintAnalysis(BaseModel):
    """
    This is the structured result produced by the LLM
    after analysing the complaete ccomplaint conversation.

    The result tells the backend:
    - Which complaint details are already known
    - Which important details are still missing
    - What question should be asked next
    """

    summary: str | None = Field(
        default=None,
        max_length=1255,
    )

    category: ComplaintCategory | None = None

    city: str | None = Field(
        default=None,
        max_length=150,
    )

    area: str|None = Field(
        default=None,
        max_length=250,
    )

    pincode: Pincode|None=None

    #Imp details still need to be collected.
    missing_fields: list[str] = Field(default_factory=list)

    #Asstant's next question, will become none when all
    # required information has been collected 
    next_question:str|None = None

    #Are all info nedded is collected
    is_complete:bool=False
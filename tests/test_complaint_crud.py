import random

from app.constants.complaint import ComplaintStatus, MessageRole
from app.database.complaint_crud import (
    add_complaint_message,
    create_complaint,
    get_user_complaint,
)
from app.database.crud import create_user
from app.database.models import Complaint, User
from app.database.session import SessionLocal
from app.schemas.auth import UserRegister


def test_create_complaint_conversation() -> None:
    """
    Test the basic complaint conversation flow.

    This verifies that:
    1. A complaint can be created.
    2. The first user message is stored.
    3. An assistant message can be added.
    4. The full conversation can be retrieved.
    """

    # Generate unique values so repeated test runs do not violate
    # the unique email and phone constraints.
    unique_number = random.randint(
        1_000_000_000,
        9_999_999_999,
    )

    user_data = UserRegister(
        name="Complaint Test User",
        email=f"complaint-{unique_number}@example.com",
        phone=str(unique_number),
        password="testpassword123",
    )

    created_user: User | None = None
    created_complaint: Complaint | None = None

    with SessionLocal() as db:
        try:
            # Create the user who will own the complaint.
            created_user = create_user(
                db=db,
                user=user_data,
            )

            # Start a complaint and store the first user message.
            created_complaint = create_complaint(
                db=db,
                user_id=created_user.id,
                first_message="The road near my house is broken.",
            )

            assert created_complaint.id is not None
            assert created_complaint.user_id == created_user.id
            assert created_complaint.status == ComplaintStatus.DRAFT

            # Store the assistant's follow-up question.
            assistant_message = add_complaint_message(
                db=db,
                complaint_id=created_complaint.id,
                role=MessageRole.ASSISTANT,
                content="Which area and pincode is this in?",
            )

            assert assistant_message.id is not None
            assert assistant_message.role == MessageRole.ASSISTANT

            # Retrieve the complaint using both complaint ID and user ID.
            retrieved_complaint = get_user_complaint(
                db=db,
                complaint_id=created_complaint.id,
                user_id=created_user.id,
            )

            assert retrieved_complaint is not None
            assert len(retrieved_complaint.messages) == 2

            # The relationship should return the messages in time order.
            assert retrieved_complaint.messages[0].role == MessageRole.USER
            assert (
                retrieved_complaint.messages[0].content
                == "The road near my house is broken."
            )

            assert (
                retrieved_complaint.messages[1].role
                == MessageRole.ASSISTANT
            )
            assert (
                retrieved_complaint.messages[1].content
                == "Which area and pincode is this in?"
            )

        finally:
            # Delete the test complaint if it was created.
            if created_complaint is not None:
                complaint = db.get(
                    Complaint,
                    created_complaint.id,
                )

                if complaint is not None:
                    db.delete(complaint)

            # Delete the temporary test user.
            if created_user is not None:
                user = db.get(
                    User,
                    created_user.id,
                )

                if user is not None:
                    db.delete(user)

            db.commit()
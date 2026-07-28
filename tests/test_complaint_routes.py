import random

from fastapi.testclient import TestClient
from app.database.models import Complaint, User
from app.database.crud import get_user_by_email
from app.database.session import SessionLocal
from app.main import app

from app.constants.complaint import ComplaintCategory
from app.schemas.complaint import (ComplaintAnalysis, 
                                   ComplaintEmailDraft,
                                   )

# TestClient acts like a frontend making HTTP requests to FastAPI.
client = TestClient(app)


def create_test_user_and_token(
    name_prefix: str,
) -> tuple[dict[str, str], dict[str, str]]:
    """
    Register a temporary user and log them in.

    Args:
        name_prefix:
            Text used to make the test user easier to identify.

    Returns:
        A tuple containing:

        1. The registration data.
        2. An Authorization header containing the user's JWT.

    Example return value:
        (
            {"email": "...", "password": "..."},
            {"Authorization": "Bearer eyJ..."},
        )
    """

    # Generate a unique 10-digit number so email and phone values
    # do not conflict with previous test runs.
    unique_number = random.randint(
        1_000_000_000,
        9_999_999_999,
    )

    registration_data = {
        "name": f"{name_prefix} User",
        "email": f"{name_prefix.lower()}-{unique_number}@example.com",
        "phone": str(unique_number),
        "password": "testpassword123",
    }

    # Register the temporary user through the real API route.
    register_response = client.post(
        "/auth/register",
        json=registration_data,
    )

    assert register_response.status_code == 201

    # Log in using the same credentials.
    login_response = client.post(
        "/auth/login",
        json={
            "email": registration_data["email"],
            "password": registration_data["password"],
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    # Protected routes expect the JWT in this HTTP header.
    auth_headers = {
        "Authorization": f"Bearer {access_token}",
    }

    return registration_data, auth_headers


def delete_test_user(email: str) -> None:
    """
    Delete a temporary test user from PostgreSQL.

    Because the User-to-Complaint relationship uses cascading deletes,
    deleting the user should also remove their complaints and messages.
    """

    with SessionLocal() as db:
        user = get_user_by_email(
            db=db,
            user_email=email,
        )

        if user is not None:
            db.delete(user)
            db.commit()



def test_complete_complaint_route_flow(
    monkeypatch,
) -> None:
    """
    Test the complete complaint API workflow with mocked AI output.

    This verifies that an authenticated user can:

    1. Start a complaint.
    2. Store the first user message.
    3. Add another user message.
    4. Run the AI complaint workflow.
    5. Update structured complaint fields.
    6. Store an assistant follow-up question.
    7. List their complaints.
    8. Retrieve the complete conversation.
    """

    def fake_analyse_complaint_conversation(
        messages: list[dict[str, str]],
    ) -> ComplaintAnalysis:
        """
        Return predictable AI output without calling Groq.

        The workflow should send both user messages to this function.
        """

        assert len(messages) == 2

        assert messages[0]["role"] == "user"
        assert (
            messages[0]["content"]
            == "The road near my house has been broken for months."
        )

        assert messages[1]["role"] == "user"
        assert (
            messages[1]["content"]
            == "The location is Vijay Nagar, pincode 482002."
        )

        return ComplaintAnalysis(
            summary=(
                "The road near the user's house in Vijay Nagar "
                "has been broken for several months."
            ),
            category=ComplaintCategory.ROAD,
            city=None,
            area="Vijay Nagar",
            pincode="482002",
            missing_fields=["city"],
            next_question="Which city is Vijay Nagar located in?",
            is_complete=False,
        )

    # Replace the real Groq function only during this test.
    #
    # We patch the name inside complaint_workflow because that is
    # where analyse_complaint_conversation() is used.
    monkeypatch.setattr(
        "app.services.complaint_workflow."
        "analyse_complaint_conversation",
        fake_analyse_complaint_conversation,
    )

    registration_data, auth_headers = create_test_user_and_token(
        name_prefix="ComplaintRoute",
    )

    try:
        # Start a new complaint conversation.
        create_response = client.post(
            "/complaints",
            json={
                "message": (
                    "The road near my house has been broken for months."
                ),
            },
            headers=auth_headers,
        )

        assert create_response.status_code == 201

        created_complaint = create_response.json()
        complaint_id = created_complaint["id"]

        assert created_complaint["status"] == "draft"
        assert created_complaint["category"] is None
        assert created_complaint["summary"] is None
        assert created_complaint["city"] is None
        assert created_complaint["area"] is None
        assert created_complaint["pincode"] is None

        # Starting a complaint should store the first user message.
        assert len(created_complaint["messages"]) == 1

        first_message = created_complaint["messages"][0]

        assert first_message["role"] == "user"
        assert (
            first_message["content"]
            == "The road near my house has been broken for months."
        )

        # Add the second user message.
        #
        # The updated route should now run the complete workflow:
        # user message -> AI analysis -> structured update ->
        # assistant follow-up question.
        message_response = client.post(
            f"/complaints/{complaint_id}/messages",
            json={
                "content": (
                    "The location is Vijay Nagar, pincode 482002."
                ),
            },
            headers=auth_headers,
        )

        assert message_response.status_code == 201

        updated_complaint = message_response.json()

        assert updated_complaint["id"] == complaint_id

        # Confirm that the AI-generated structured information was
        # stored in the complaint row.
        assert (
            updated_complaint["summary"]
            == (
                "The road near the user's house in Vijay Nagar "
                "has been broken for several months."
            )
        )
        assert updated_complaint["category"] == "road"
        assert updated_complaint["city"] is None
        assert updated_complaint["area"] == "Vijay Nagar"
        assert updated_complaint["pincode"] == "482002"

        # The conversation should now contain:
        # 1. Original user message.
        # 2. Second user message.
        # 3. Assistant follow-up question.
        assert len(updated_complaint["messages"]) == 3

        assert updated_complaint["messages"][0]["role"] == "user"
        assert (
            updated_complaint["messages"][0]["content"]
            == "The road near my house has been broken for months."
        )

        assert updated_complaint["messages"][1]["role"] == "user"
        assert (
            updated_complaint["messages"][1]["content"]
            == "The location is Vijay Nagar, pincode 482002."
        )

        assert updated_complaint["messages"][2]["role"] == "assistant"
        assert (
            updated_complaint["messages"][2]["content"]
            == "Which city is Vijay Nagar located in?"
        )

        # Retrieve all complaints belonging to the authenticated user.
        list_response = client.get(
            "/complaints",
            headers=auth_headers,
        )

        assert list_response.status_code == 200

        complaints = list_response.json()

        assert any(
            complaint["id"] == complaint_id
            for complaint in complaints
        )

        listed_complaint = next(
            complaint
            for complaint in complaints
            if complaint["id"] == complaint_id
        )

        assert listed_complaint["category"] == "road"
        assert listed_complaint["area"] == "Vijay Nagar"
        assert listed_complaint["pincode"] == "482002"

        # Retrieve the complaint with its complete conversation.
        detail_response = client.get(
            f"/complaints/{complaint_id}",
            headers=auth_headers,
        )

        assert detail_response.status_code == 200

        complaint_detail = detail_response.json()

        assert complaint_detail["id"] == complaint_id
        assert complaint_detail["category"] == "road"
        assert complaint_detail["area"] == "Vijay Nagar"
        assert complaint_detail["pincode"] == "482002"

        assert len(complaint_detail["messages"]) == 3

        assert complaint_detail["messages"][0]["role"] == "user"
        assert complaint_detail["messages"][1]["role"] == "user"
        assert complaint_detail["messages"][2]["role"] == "assistant"

        assert (
            complaint_detail["messages"][2]["content"]
            == "Which city is Vijay Nagar located in?"
        )

    finally:
        # Remove the temporary user and all related complaint data,
        # even when an assertion fails.
        delete_test_user(registration_data["email"])


def test_complaint_routes_require_authentication() -> None:
    """
    Confirm that complaint routes reject requests without a JWT.
    """

    response = client.get("/complaints")

    assert response.status_code == 401


def test_user_cannot_access_another_users_complaint() -> None:
    """
    Confirm that one authenticated user cannot retrieve a complaint
    belonging to another authenticated user.
    """

    first_user_data, first_user_headers = create_test_user_and_token(
        name_prefix="ComplaintOwner",
    )

    second_user_data, second_user_headers = create_test_user_and_token(
        name_prefix="ComplaintIntruder",
    )

    try:
        # The first user creates a complaint.
        create_response = client.post(
            "/complaints",
            json={
                "message": "There is no water supply in my locality.",
            },
            headers=first_user_headers,
        )

        assert create_response.status_code == 201

        complaint_id = create_response.json()["id"]

        # The second user attempts to retrieve the first user's complaint.
        forbidden_response = client.get(
            f"/complaints/{complaint_id}",
            headers=second_user_headers,
        )

        # Returning 404 avoids revealing whether another user's
        # complaint with that ID exists.
        assert forbidden_response.status_code == 404
        assert forbidden_response.json() == {
            "detail": "Complaint not found",
        }

    finally:
        delete_test_user(first_user_data["email"])
        delete_test_user(second_user_data["email"])


def test_complaint_becomes_awaiting_approval_when_complete(
    monkeypatch,
) -> None:
    """
    Confirm that a completed complaint moves from draft
    to awaiting_approval and no further AI question is stored.
    """

    def fake_complete_analysis(
        messages: list[dict[str, str]],
    ) -> ComplaintAnalysis:
        """
        Simulate the AI deciding that all required details
        are available.
        """

        assert len(messages) == 2

        return ComplaintAnalysis(
            summary=(
                "The main road in Vijay Nagar, Jabalpur, "
                "has been badly damaged for three months."
            ),
            category=ComplaintCategory.ROAD,
            city="Jabalpur",
            area="Vijay Nagar",
            pincode="482002",
            missing_fields=[],
            next_question=None,
            is_complete=True,
        )

    monkeypatch.setattr(
        "app.services.complaint_workflow."
        "analyse_complaint_conversation",
        fake_complete_analysis,
    )

    registration_data, auth_headers = create_test_user_and_token(
        name_prefix="CompleteComplaint",
    )

    try:
        create_response = client.post(
            "/complaints",
            json={
                "message": (
                    "The main road in Vijay Nagar is badly damaged."
                ),
            },
            headers=auth_headers,
        )

        assert create_response.status_code == 201

        complaint_id = create_response.json()["id"]

        message_response = client.post(
            f"/complaints/{complaint_id}/messages",
            json={
                "content": (
                    "It is in Jabalpur, pincode 482002, "
                    "and has been damaged for three months."
                ),
            },
            headers=auth_headers,
        )

        assert message_response.status_code == 201

        complaint = message_response.json()

        assert complaint["status"] == "awaiting_approval"
        assert complaint["category"] == "road"
        assert complaint["city"] == "Jabalpur"
        assert complaint["area"] == "Vijay Nagar"
        assert complaint["pincode"] == "482002"

        # Only the two user messages should exist.
        # No assistant follow-up question should be added.
        assert len(complaint["messages"]) == 2

        assert complaint["messages"][0]["role"] == "user"
        assert complaint["messages"][1]["role"] == "user"

    finally:
        delete_test_user(registration_data["email"])


def test_completed_complaint_rejects_new_messages(
    monkeypatch,
) -> None:
    """
    Confirm that a complaint stops accepting ordinary chat messages
    after it reaches awaiting_approval.
    """

    def fake_complete_analysis(
        messages: list[dict[str, str]],
    ) -> ComplaintAnalysis:
        return ComplaintAnalysis(
            summary=(
                "The road in Vijay Nagar, Jabalpur, "
                "has been damaged for three months."
            ),
            category=ComplaintCategory.ROAD,
            city="Jabalpur",
            area="Vijay Nagar",
            pincode="482002",
            missing_fields=[],
            next_question=None,
            is_complete=True,
        )

    monkeypatch.setattr(
        "app.services.complaint_workflow."
        "analyse_complaint_conversation",
        fake_complete_analysis,
    )

    registration_data, auth_headers = create_test_user_and_token(
        name_prefix="ClosedComplaint",
    )

    try:
        create_response = client.post(
            "/complaints",
            json={
                "message": "The road in Vijay Nagar is damaged.",
            },
            headers=auth_headers,
        )

        assert create_response.status_code == 201

        complaint_id = create_response.json()["id"]

        complete_response = client.post(
            f"/complaints/{complaint_id}/messages",
            json={
                "content": (
                    "It is in Jabalpur, pincode 482002, "
                    "and has been damaged for three months."
                ),
            },
            headers=auth_headers,
        )

        assert complete_response.status_code == 201
        assert (
            complete_response.json()["status"]
            == "awaiting_approval"
        )

        # Try to add another message after completion.
        rejected_response = client.post(
            f"/complaints/{complaint_id}/messages",
            json={
                "content": "I want to add one more detail.",
            },
            headers=auth_headers,
        )

        assert rejected_response.status_code == 409
        assert rejected_response.json() == {
            "detail": (
                "This complaint is no longer accepting "
                "conversation messages."
            )
        }

    finally:
        delete_test_user(registration_data["email"])


def test_generate_complaint_email_draft(
    monkeypatch,
) -> None:
    """
    Confirm that a completed complaint can generate and save
    an email draft without calling the real Groq API.
    """

    def fake_complete_analysis(
        messages: list[dict[str, str]],
    ) -> ComplaintAnalysis:
        """
        Simulate the complaint-analysis model deciding that
        the complaint is complete.
        """

        return ComplaintAnalysis(
            summary=(
                "The main road in Vijay Nagar, Jabalpur, "
                "has been badly damaged for three months."
            ),
            category=ComplaintCategory.ROAD,
            city="Jabalpur",
            area="Vijay Nagar",
            pincode="482002",
            missing_fields=[],
            next_question=None,
            is_complete=True,
        )

    def fake_generate_complaint_email_draft(
        complaint: Complaint,
        user: User,
    ) -> ComplaintEmailDraft:
        """
        Return a predictable email draft without calling Groq.
        """

        assert user.name
        assert complaint.city == "Jabalpur"
        assert complaint.area == "Vijay Nagar"
        assert complaint.pincode == "482002"

        return ComplaintEmailDraft(
            subject="Request for repair of damaged road in Vijay Nagar",
            body=(
                "Dear Sir/Madam,\n\n"
                f"I, {user.name}, wish to report that the main road "
                "in Vijay Nagar, Jabalpur, pincode 482002, has been "
                "badly damaged for three months.\n\n"
                "I request timely inspection and appropriate action.\n\n"
                f"Sincerely,\n{user.name}"
            ),
        )

    monkeypatch.setattr(
        "app.services.complaint_workflow."
        "analyse_complaint_conversation",
        fake_complete_analysis,
    )

    monkeypatch.setattr(
        "app.services.complaint_email_workflow."
        "generate_complaint_email_draft",
        fake_generate_complaint_email_draft,
    )

    registration_data, auth_headers = create_test_user_and_token(
        name_prefix="EmailDraft",
    )

    try:
        create_response = client.post(
            "/complaints",
            json={
                "message": (
                    "The main road in Vijay Nagar is badly damaged."
                ),
            },
            headers=auth_headers,
        )

        assert create_response.status_code == 201

        complaint_id = create_response.json()["id"]

        # Complete the complaint so its status becomes
        # awaiting_approval.
        complete_response = client.post(
            f"/complaints/{complaint_id}/messages",
            json={
                "content": (
                    "It is in Jabalpur, pincode 482002, "
                    "and has been damaged for three months."
                ),
            },
            headers=auth_headers,
        )

        assert complete_response.status_code == 201
        assert (
            complete_response.json()["status"]
            == "awaiting_approval"
        )

        # Generate and save the email draft.
        draft_response = client.post(
            f"/complaints/{complaint_id}/email-draft",
            headers=auth_headers,
        )

        assert draft_response.status_code == 201

        complaint = draft_response.json()

        assert complaint["id"] == complaint_id

        assert (
            complaint["email_subject"]
            == "Request for repair of damaged road in Vijay Nagar"
        )

        assert complaint["email_body"] is not None
        assert registration_data["name"] in complaint["email_body"]
        assert "Vijay Nagar" in complaint["email_body"]

    finally:
        delete_test_user(registration_data["email"])











def test_edit_and_approve_complaint_email_draft(
    monkeypatch,
) -> None:
    """
    Verify that a user can:

    1. Complete a complaint.
    2. Generate an email draft.
    3. Edit the saved draft.
    4. Explicitly approve the edited draft.
    """

    def fake_complete_analysis(
        messages: list[dict[str, str]],
    ) -> ComplaintAnalysis:
        """
        Simulate the AI deciding that the complaint has enough details.
        """

        return ComplaintAnalysis(
            summary=(
                "The main road in Vijay Nagar, Jabalpur, "
                "has been badly damaged for three months."
            ),
            category=ComplaintCategory.ROAD,
            city="Jabalpur",
            area="Vijay Nagar",
            pincode="482002",
            missing_fields=[],
            next_question=None,
            is_complete=True,
        )

    def fake_generate_complaint_email_draft(
        complaint: Complaint,
        user: User,
    ) -> ComplaintEmailDraft:
        """
        Return a predictable email draft without calling Groq.
        """

        return ComplaintEmailDraft(
            subject="Request for repair of damaged road",
            body=(
                "Dear Sir/Madam,\n\n"
                f"I, {user.name}, wish to report a damaged road "
                "in Vijay Nagar, Jabalpur, pincode 482002.\n\n"
                "Please inspect the location and take appropriate action.\n\n"
                f"Sincerely,\n{user.name}"
            ),
        )

    monkeypatch.setattr(
        "app.services.complaint_workflow."
        "analyse_complaint_conversation",
        fake_complete_analysis,
    )

    monkeypatch.setattr(
        "app.services.complaint_email_workflow."
        "generate_complaint_email_draft",
        fake_generate_complaint_email_draft,
    )

    registration_data, auth_headers = create_test_user_and_token(
        name_prefix="ApprovalFlow",
    )

    try:
        # Start a new complaint.
        create_response = client.post(
            "/complaints",
            json={
                "message": (
                    "The main road in Vijay Nagar is badly damaged."
                ),
            },
            headers=auth_headers,
        )

        assert create_response.status_code == 201

        complaint_id = create_response.json()["id"]

        # Submit enough information to complete the complaint.
        complete_response = client.post(
            f"/complaints/{complaint_id}/messages",
            json={
                "content": (
                    "It is in Jabalpur, pincode 482002, "
                    "and has been damaged for three months."
                ),
            },
            headers=auth_headers,
        )

        assert complete_response.status_code == 201
        assert (
            complete_response.json()["status"]
            == "awaiting_approval"
        )

        # Generate and save the initial AI draft.
        generate_response = client.post(
            f"/complaints/{complaint_id}/email-draft",
            headers=auth_headers,
        )

        assert generate_response.status_code == 201
        assert generate_response.json()["email_subject"] is not None
        assert generate_response.json()["email_body"] is not None

        edited_subject = (
            "Urgent request for repair of damaged road in Vijay Nagar"
        )

        edited_body = (
            "Dear Sir/Madam,\n\n"
            "I wish to report that the main road in Vijay Nagar, "
            "Jabalpur, pincode 482002, has remained badly damaged "
            "for the past three months. The damaged road is creating "
            "difficulty and safety risks for commuters.\n\n"
            "Please arrange an inspection and complete the necessary "
            "repairs at the earliest.\n\n"
            f"Sincerely,\n{registration_data['name']}"
        )

        # Edit the generated draft.
        edit_response = client.patch(
            f"/complaints/{complaint_id}/email-draft",
            json={
                "subject": edited_subject,
                "body": edited_body,
            },
            headers=auth_headers,
        )

        assert edit_response.status_code == 200

        edited_complaint = edit_response.json()

        assert edited_complaint["email_subject"] == edited_subject
        assert edited_complaint["email_body"] == edited_body

        # Editing must not approve the complaint.
        assert (
            edited_complaint["status"]
            == "awaiting_approval"
        )

        # Explicitly approve the edited draft.
        approve_response = client.post(
            f"/complaints/{complaint_id}/approve",
            headers=auth_headers,
        )

        assert approve_response.status_code == 200

        approved_complaint = approve_response.json()

        assert approved_complaint["id"] == complaint_id
        assert approved_complaint["status"] == "approved"
        assert (
            approved_complaint["email_subject"]
            == edited_subject
        )
        assert approved_complaint["email_body"] == edited_body

    finally:
        delete_test_user(registration_data["email"])
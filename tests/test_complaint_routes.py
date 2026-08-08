import random

from fastapi.testclient import TestClient

from app.constants.complaint import ComplaintCategory
from app.database.crud import get_user_by_email
from app.database.models import Complaint, User
from app.database.session import SessionLocal
from app.main import app
from app.schemas.complaint import (
    ComplaintAnalysis,
    ComplaintEmailDraft,
)
from app.routers.complaints import get_email_sender

# TestClient behaves like a frontend calling the FastAPI application.
client = TestClient(app)


ANALYSIS_PATCH_TARGET = (
    "app.graphs.complaint_graph.analyse_complaint_conversation"
)

EMAIL_DRAFT_PATCH_TARGET = (
    "app.services.complaint_email_workflow."
    "generate_complaint_email_draft"
)


FIRST_ROAD_MESSAGE = (
    "The main road in Vijay Nagar is badly damaged."
)

ROAD_DETAILS_MESSAGE = (
    "It is in Jabalpur, pincode 482005, "
    "and has been damaged for three months."
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def create_test_user_and_token(
    name_prefix: str,
) -> tuple[dict[str, str], dict[str, str]]:
    """
    Register a temporary user and log in through the real API routes.

    Returns:
        1. Registration data.
        2. Authorization header containing the user's JWT.
    """

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

    register_response = client.post(
        "/auth/register",
        json=registration_data,
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={
            "email": registration_data["email"],
            "password": registration_data["password"],
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    auth_headers = {
        "Authorization": f"Bearer {access_token}",
    }

    return registration_data, auth_headers


def delete_test_user(email: str) -> None:
    """
    Delete a temporary test user and its cascade-related data.
    """

    with SessionLocal() as db:
        user = get_user_by_email(
            db=db,
            user_email=email,
        )

        if user is not None:
            db.delete(user)
            db.commit()


def count_user_messages(
    messages: list[dict[str, str]],
) -> int:
    """Count only user messages in a serialized conversation."""

    return sum(
        message["role"] == "user"
        for message in messages
    )


def incomplete_analysis(
    messages: list[dict[str, str]],
) -> ComplaintAnalysis:
    """
    Return an incomplete result suitable for tests that only start
    a complaint and do not need it to become complete.
    """

    return ComplaintAnalysis(
        summary="A civic issue has been reported by the user.",
        category=ComplaintCategory.ROAD,
        city=None,
        area=None,
        pincode=None,
        missing_fields=["city", "area", "pincode"],
        next_question=(
            "Which city, area and pincode is this issue located in?"
        ),
        is_complete=False,
    )


def two_turn_complete_analysis(
    messages: list[dict[str, str]],
) -> ComplaintAnalysis:
    """
    Simulate a two-turn complaint conversation.

    First graph run:
        The first user message is present, so the complaint remains
        incomplete and an assistant clarification is created.

    Second graph run:
        The user's clarification is present, so the complaint becomes
        complete and can be matched to an authority.
    """

    user_message_count = count_user_messages(messages)

    if user_message_count == 1:
        return ComplaintAnalysis(
            summary=(
                "The main road in Vijay Nagar is badly damaged."
            ),
            category=ComplaintCategory.ROAD,
            city=None,
            area="Vijay Nagar",
            pincode=None,
            missing_fields=["city", "pincode"],
            next_question=(
                "Which city and pincode is Vijay Nagar located in?"
            ),
            is_complete=False,
        )

    return ComplaintAnalysis(
        summary=(
            "The main road in Vijay Nagar, Jabalpur, "
            "has been badly damaged for three months."
        ),
        category=ComplaintCategory.ROAD,
        city="Jabalpur",
        area="Vijay Nagar",
        pincode="482005",
        missing_fields=[],
        next_question=None,
        is_complete=True,
    )


def complete_road_complaint(
    auth_headers: dict[str, str],
) -> tuple[int, dict]:
    """
    Create a complaint and complete it through the real HTTP routes.

    The caller must patch the graph analysis function before calling
    this helper.
    """

    create_response = client.post(
        "/complaints",
        json={"message": FIRST_ROAD_MESSAGE},
        headers=auth_headers,
    )

    assert create_response.status_code == 201

    complaint_id = create_response.json()["id"]

    complete_response = client.post(
        f"/complaints/{complaint_id}/messages",
        json={"content": ROAD_DETAILS_MESSAGE},
        headers=auth_headers,
    )

    assert complete_response.status_code == 201

    complaint = complete_response.json()

    assert complaint["status"] == "awaiting_approval"

    return complaint_id, complaint


# ---------------------------------------------------------------------------
# Complaint conversation route tests
# ---------------------------------------------------------------------------


def test_complete_complaint_route_flow(
    monkeypatch,
) -> None:
    """
    Verify the real LangGraph-powered incomplete conversation flow.

    The graph runs once after complaint creation and again after the
    user's next message.
    """

    def fake_analysis(
        messages: list[dict[str, str]],
    ) -> ComplaintAnalysis:
        user_message_count = count_user_messages(messages)

        if user_message_count == 1:
            assert messages[0] == {
                "role": "user",
                "content": (
                    "The road near my house has been broken for months."
                ),
            }

            return ComplaintAnalysis(
                summary=(
                    "The road near the user's house has been "
                    "broken for months."
                ),
                category=ComplaintCategory.ROAD,
                city=None,
                area=None,
                pincode=None,
                missing_fields=["city", "area", "pincode"],
                next_question=(
                    "Which city, area and pincode is this issue located in?"
                ),
                is_complete=False,
            )

        assert user_message_count == 2

        return ComplaintAnalysis(
            summary=(
                "The road near the user's house in Vijay Nagar "
                "has been broken for several months."
            ),
            category=ComplaintCategory.ROAD,
            city=None,
            area="Vijay Nagar",
            pincode="482005",
            missing_fields=["city"],
            next_question="Which city is Vijay Nagar located in?",
            is_complete=False,
        )

    monkeypatch.setattr(
        ANALYSIS_PATCH_TARGET,
        fake_analysis,
    )

    registration_data, auth_headers = create_test_user_and_token(
        name_prefix="ComplaintRoute",
    )

    try:
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

        # The start route now invokes LangGraph immediately.
        assert created_complaint["status"] == "draft"
        assert created_complaint["category"] == "road"
        assert created_complaint["summary"] is not None
        assert created_complaint["city"] is None
        assert created_complaint["area"] is None
        assert created_complaint["pincode"] is None

        # First user message + first assistant clarification.
        assert len(created_complaint["messages"]) == 2
        assert created_complaint["messages"][0]["role"] == "user"
        assert created_complaint["messages"][1]["role"] == "assistant"
        assert created_complaint["messages"][1]["content"] == (
            "Which city, area and pincode is this issue located in?"
        )

        message_response = client.post(
            f"/complaints/{complaint_id}/messages",
            json={
                "content": (
                    "The location is Vijay Nagar, pincode 482005."
                ),
            },
            headers=auth_headers,
        )

        assert message_response.status_code == 201

        updated_complaint = message_response.json()

        assert updated_complaint["id"] == complaint_id
        assert updated_complaint["status"] == "draft"
        assert updated_complaint["category"] == "road"
        assert updated_complaint["city"] is None
        assert updated_complaint["area"] == "Vijay Nagar"
        assert updated_complaint["pincode"] == "482005"

        # First user + first assistant + second user + second assistant.
        assert len(updated_complaint["messages"]) == 4
        assert [
            message["role"]
            for message in updated_complaint["messages"]
        ] == [
            "user",
            "assistant",
            "user",
            "assistant",
        ]
        assert updated_complaint["messages"][3]["content"] == (
            "Which city is Vijay Nagar located in?"
        )

        list_response = client.get(
            "/complaints",
            headers=auth_headers,
        )

        assert list_response.status_code == 200

        listed_complaint = next(
            complaint
            for complaint in list_response.json()
            if complaint["id"] == complaint_id
        )

        assert listed_complaint["category"] == "road"
        assert listed_complaint["area"] == "Vijay Nagar"
        assert listed_complaint["pincode"] == "482005"

        detail_response = client.get(
            f"/complaints/{complaint_id}",
            headers=auth_headers,
        )

        assert detail_response.status_code == 200

        complaint_detail = detail_response.json()

        assert complaint_detail["id"] == complaint_id
        assert len(complaint_detail["messages"]) == 4
        assert complaint_detail["messages"][3]["content"] == (
            "Which city is Vijay Nagar located in?"
        )

    finally:
        delete_test_user(registration_data["email"])


def test_complaint_routes_require_authentication() -> None:
    """Confirm complaint routes reject requests without a JWT."""

    response = client.get("/complaints")

    assert response.status_code == 401


def test_user_cannot_access_another_users_complaint(
    monkeypatch,
) -> None:
    """
    Confirm one user cannot retrieve a complaint owned by another user.
    """

    monkeypatch.setattr(
        ANALYSIS_PATCH_TARGET,
        incomplete_analysis,
    )

    first_user_data, first_user_headers = create_test_user_and_token(
        name_prefix="ComplaintOwner",
    )

    second_user_data, second_user_headers = create_test_user_and_token(
        name_prefix="ComplaintIntruder",
    )

    try:
        create_response = client.post(
            "/complaints",
            json={
                "message": "There is no water supply in my locality.",
            },
            headers=first_user_headers,
        )

        assert create_response.status_code == 201

        complaint_id = create_response.json()["id"]

        forbidden_response = client.get(
            f"/complaints/{complaint_id}",
            headers=second_user_headers,
        )

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
    Confirm a completed complaint stores canonical city and authority
    information and moves to awaiting_approval.
    """

    monkeypatch.setattr(
        ANALYSIS_PATCH_TARGET,
        two_turn_complete_analysis,
    )

    registration_data, auth_headers = create_test_user_and_token(
        name_prefix="CompleteComplaint",
    )

    try:
        complaint_id, complaint = complete_road_complaint(
            auth_headers,
        )

        assert complaint["category"] == "road"
        assert complaint["city"] == "Jabalpur"
        assert complaint["area"] == "Vijay Nagar"
        assert complaint["pincode"] == "482005"
        assert complaint["authority"] is not None

        with SessionLocal() as db:
            saved_complaint = db.get(
                Complaint,
                complaint_id,
            )

            assert saved_complaint is not None
            assert saved_complaint.city == "Jabalpur"
            assert saved_complaint.city_id is not None
            assert saved_complaint.authority_id is not None
            assert saved_complaint.city_record is not None
            assert saved_complaint.city_record.name == "Jabalpur"

        # First user + assistant clarification + second user.
        # No new assistant message is added after completion.
        assert len(complaint["messages"]) == 3
        assert [
            message["role"]
            for message in complaint["messages"]
        ] == [
            "user",
            "assistant",
            "user",
        ]

    finally:
        delete_test_user(registration_data["email"])


def test_completed_complaint_rejects_new_messages(
    monkeypatch,
) -> None:
    """
    Confirm a complaint stops accepting conversation messages after
    it reaches awaiting_approval.
    """

    monkeypatch.setattr(
        ANALYSIS_PATCH_TARGET,
        two_turn_complete_analysis,
    )

    registration_data, auth_headers = create_test_user_and_token(
        name_prefix="ClosedComplaint",
    )

    try:
        complaint_id, _ = complete_road_complaint(
            auth_headers,
        )

        rejected_response = client.post(
            f"/complaints/{complaint_id}/messages",
            json={"content": "I want to add one more detail."},
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


# ---------------------------------------------------------------------------
# Email-draft and approval route tests
# ---------------------------------------------------------------------------


def test_generate_complaint_email_draft(
    monkeypatch,
) -> None:
    """
    Confirm a completed complaint can generate and save an email draft
    without calling the real LLM provider.
    """

    def fake_generate_complaint_email_draft(
        complaint: Complaint,
        user: User,
    ) -> ComplaintEmailDraft:
        assert user.name
        assert complaint.city == "Jabalpur"
        assert complaint.area == "Vijay Nagar"
        assert complaint.pincode == "482005"
        assert complaint.authority is not None

        return ComplaintEmailDraft(
            subject=(
                "Request for repair of damaged road in Vijay Nagar"
            ),
            body=(
                "Dear Sir/Madam,\n\n"
                f"I, {user.name}, wish to report that the main road "
                "in Vijay Nagar, Jabalpur, pincode 482005, has been "
                "badly damaged for three months.\n\n"
                "I request timely inspection and appropriate action.\n\n"
                f"Sincerely,\n{user.name}"
            ),
        )

    monkeypatch.setattr(
        ANALYSIS_PATCH_TARGET,
        two_turn_complete_analysis,
    )
    monkeypatch.setattr(
        EMAIL_DRAFT_PATCH_TARGET,
        fake_generate_complaint_email_draft,
    )

    registration_data, auth_headers = create_test_user_and_token(
        name_prefix="EmailDraft",
    )

    try:
        complaint_id, _ = complete_road_complaint(
            auth_headers,
        )

        draft_response = client.post(
            f"/complaints/{complaint_id}/email-draft",
            headers=auth_headers,
        )

        assert draft_response.status_code == 201

        complaint = draft_response.json()

        assert complaint["id"] == complaint_id
        assert complaint["email_subject"] == (
            "Request for repair of damaged road in Vijay Nagar"
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
    Verify that a user can generate, edit and approve an email draft.
    """

    def fake_generate_complaint_email_draft(
        complaint: Complaint,
        user: User,
    ) -> ComplaintEmailDraft:
        assert complaint.authority is not None

        return ComplaintEmailDraft(
            subject="Request for repair of damaged road",
            body=(
                "Dear Sir/Madam,\n\n"
                f"I, {user.name}, wish to report a damaged road "
                "in Vijay Nagar, Jabalpur, pincode 482005.\n\n"
                "Please inspect the location and take appropriate action.\n\n"
                f"Sincerely,\n{user.name}"
            ),
        )

    monkeypatch.setattr(
        ANALYSIS_PATCH_TARGET,
        two_turn_complete_analysis,
    )
    monkeypatch.setattr(
        EMAIL_DRAFT_PATCH_TARGET,
        fake_generate_complaint_email_draft,
    )

    registration_data, auth_headers = create_test_user_and_token(
        name_prefix="ApprovalFlow",
    )

    try:
        complaint_id, _ = complete_road_complaint(
            auth_headers,
        )

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
            "Jabalpur, pincode 482005, has remained badly damaged "
            "for the past three months. The damaged road is creating "
            "difficulty and safety risks for commuters.\n\n"
            "Please arrange an inspection and complete the necessary "
            "repairs at the earliest.\n\n"
            f"Sincerely,\n{registration_data['name']}"
        )

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
        assert edited_complaint["status"] == "awaiting_approval"

        approve_response = client.post(
            f"/complaints/{complaint_id}/approve",
            headers=auth_headers,
        )

        assert approve_response.status_code == 200

        approved_complaint = approve_response.json()

        assert approved_complaint["id"] == complaint_id
        assert approved_complaint["status"] == "approved"
        assert approved_complaint["email_subject"] == edited_subject
        assert approved_complaint["email_body"] == edited_body

    finally:
        delete_test_user(registration_data["email"])





class RecordingEmailSender:
    """
    Fake API email sender.

    It records outgoing emails so route tests can verify delivery
    without sending a real email.
    """

    def __init__(self) -> None:
        self.sent_emails: list[dict[str, str]] = []

    def send_email(
        self,
        *,
        recipient: str,
        subject: str,
        body: str,
    ) -> None:
        self.sent_emails.append(
            {
                "recipient": recipient,
                "subject": subject,
                "body": body,
            }
        )




def test_send_approved_complaint_email_route(
    monkeypatch,
) -> None:
    """
    Verify the complete HTTP flow:

    complaint
    → complete
    → generate draft
    → approve
    → send
    → status SENT
    """

    def fake_generate_complaint_email_draft(
        complaint: Complaint,
        user: User,
    ) -> ComplaintEmailDraft:
        assert complaint.authority is not None

        return ComplaintEmailDraft(
            subject="Request for repair of damaged road",
            body=(
                "Dear Sir/Madam,\n\n"
                "The main road in Vijay Nagar, Jabalpur, "
                "pincode 482005, has been badly damaged.\n\n"
                "Please inspect the location and take appropriate "
                "action.\n\n"
                f"Sincerely,\n{user.name}"
            ),
        )

    monkeypatch.setattr(
        ANALYSIS_PATCH_TARGET,
        two_turn_complete_analysis,
    )

    monkeypatch.setattr(
        EMAIL_DRAFT_PATCH_TARGET,
        fake_generate_complaint_email_draft,
    )

    sender = RecordingEmailSender()

    # FastAPI will inject our fake sender instead of
    # ConsoleEmailSender during this test.
    app.dependency_overrides[get_email_sender] = lambda: sender

    registration_data, auth_headers = create_test_user_and_token(
        name_prefix="SendComplaint",
    )

    try:
        complaint_id, _ = complete_road_complaint(
            auth_headers,
        )

        draft_response = client.post(
            f"/complaints/{complaint_id}/email-draft",
            headers=auth_headers,
        )

        assert draft_response.status_code == 201

        approve_response = client.post(
            f"/complaints/{complaint_id}/approve",
            headers=auth_headers,
        )

        assert approve_response.status_code == 200
        assert approve_response.json()["status"] == "approved"

        send_response = client.post(
            f"/complaints/{complaint_id}/send",
            headers=auth_headers,
        )

        assert send_response.status_code == 200

        sent_complaint = send_response.json()

        assert sent_complaint["id"] == complaint_id
        assert sent_complaint["status"] == "sent"

        assert len(sender.sent_emails) == 1

        sent_email = sender.sent_emails[0]

        assert sent_email["subject"] == (
            "Request for repair of damaged road"
        )
        assert sent_email["body"] == sent_complaint["email_body"]

        # Recipient must come from the matched authority,
        # not from user-controlled request data.
        assert sent_email["recipient"] == (
            sent_complaint["authority"]["email"]
        )

    finally:
        app.dependency_overrides.pop(
            get_email_sender,
            None,
        )

        delete_test_user(
            registration_data["email"],
        )
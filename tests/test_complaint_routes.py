import random

from fastapi.testclient import TestClient

from app.database.crud import get_user_by_email
from app.database.session import SessionLocal
from app.main import app


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


def test_complete_complaint_route_flow() -> None:
    """
    Test the complete basic complaint API workflow.

    This verifies that an authenticated user can:

    1. Start a complaint.
    2. Receive the first stored message.
    3. Add another message.
    4. List their complaints.
    5. Retrieve one complaint with its full conversation.
    """

    registration_data, auth_headers = create_test_user_and_token(
        name_prefix="ComplaintRoute",
    )

    try:
        # Start a complaint conversation.
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

        # Store the generated complaint ID for later requests.
        complaint_id = created_complaint["id"]

        assert created_complaint["status"] == "draft"
        assert created_complaint["category"] is None

        # Starting a complaint should also store the first user message.
        assert len(created_complaint["messages"]) == 1

        first_message = created_complaint["messages"][0]

        assert first_message["role"] == "user"
        assert (
            first_message["content"]
            == "The road near my house has been broken for months."
        )

        # Add another user message to the same complaint conversation.
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

        added_message = message_response.json()

        assert added_message["complaint_id"] == complaint_id
        assert added_message["role"] == "user"
        assert (
            added_message["content"]
            == "The location is Vijay Nagar, pincode 482002."
        )

        # Retrieve all complaints belonging to this user.
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

        # Retrieve one complaint with its complete conversation.
        detail_response = client.get(
            f"/complaints/{complaint_id}",
            headers=auth_headers,
        )

        assert detail_response.status_code == 200

        complaint_detail = detail_response.json()

        assert complaint_detail["id"] == complaint_id
        assert len(complaint_detail["messages"]) == 2

        assert complaint_detail["messages"][0]["role"] == "user"
        assert complaint_detail["messages"][1]["role"] == "user"

    finally:
        # Remove the temporary user and their complaint data,
        # even if an assertion fails.
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
        # The first user creates the complaint.
        create_response = client.post(
            "/complaints",
            json={
                "message": "There is no water supply in my locality.",
            },
            headers=first_user_headers,
        )

        assert create_response.status_code == 201

        complaint_id = create_response.json()["id"]

        # The second user tries to retrieve the first user's complaint.
        forbidden_response = client.get(
            f"/complaints/{complaint_id}",
            headers=second_user_headers,
        )

        # Your route intentionally returns 404 instead of 403.
        #
        # This avoids revealing whether another user's complaint
        # with that ID actually exists.
        assert forbidden_response.status_code == 404
        assert forbidden_response.json() == {
            "detail": "Complaint not found",
        }

    finally:
        delete_test_user(first_user_data["email"])
        delete_test_user(second_user_data["email"])
import random

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get('/health')

    assert response.status_code ==200
    assert response.json() == {'status':'healthy'}


def test_register_and_login_user() -> None:
    unique_number = random.randint(1_000_000_000, 9_999_999_999)
    registration_data = {
        "name": "Test User",
        "email": f"test-{unique_number}@example.com",
        "phone": str(unique_number),
        "password": "testpassword123",
    }

    register_response = client.post(
        '/auth/register',
        json=registration_data,
    )# returns User

    assert register_response.status_code == 201
    assert register_response.json()['email'] == registration_data['email']
    assert 'hashed_password' not in register_response.json()
    assert 'password' not in register_response.json()

    login_response = client.post(
        '/auth/login',
        json={
            "email": registration_data["email"],
            "password": registration_data["password"],
        },
    )

    assert login_response.status_code == 200

    response_data = login_response.json()

    assert 'access_token' in response_data
    assert response_data['token_type'] == 'bearer'

def test_login_with_wrong_password() -> None:
    response = client.post(
        "/auth/login",
        json={
            "email": "does-not-exist@example.com",
            "password": "wrongpassword",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid email or password",
    }


def test_users_me_with_valid_token() -> None:
    """
    Register a temporary user, log in, and use the returned JWT
    to access the protected GET /users/me endpoint.
    """

    import random

    unique_number = random.randint(1_000_000_000, 9_999_999_999)

    registration_data = {
        "name": "Protected Route Test User",
        "email": f"protected-{unique_number}@example.com",
        "phone": str(unique_number),
        "password": "testpassword123",
    }

    # Create a user that we can authenticate as.
    register_response = client.post(
        "/auth/register",
        json=registration_data,
    )

    assert register_response.status_code == 201

    # Log in and receive a JWT access token.
    login_response = client.post(
        "/auth/login",
        json={
            "email": registration_data["email"],
            "password": registration_data["password"],
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    # Send the token using the standard Authorization header.
    profile_response = client.get(
        "/users/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert profile_response.status_code == 200

    profile_data = profile_response.json()

    assert profile_data["email"] == registration_data["email"]
    assert profile_data["name"] == registration_data["name"]
    assert "password" not in profile_data
    assert "hashed_password" not in profile_data


def test_users_me_without_token() -> None:
    """
    Confirm that unauthenticated requests cannot access /users/me.
    """

    response = client.get("/users/me")

    assert response.status_code == 401
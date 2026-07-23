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
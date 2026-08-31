from app.models import UserRole
from tests.conftest import auth_headers


def test_login_succeeds_with_correct_credentials(client, recruiter):
    response = client.post(
        "/auth/login", json={"email": "recruiter@example.com", "password": "testpassword123"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["user"]["email"] == "recruiter@example.com"
    assert body["user"]["role"] == "recruiter"


def test_login_fails_with_wrong_password(client, recruiter):
    response = client.post(
        "/auth/login", json={"email": "recruiter@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401


def test_login_fails_for_unknown_email(client):
    response = client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": "whatever123"}
    )
    assert response.status_code == 401


def test_login_rejects_malformed_email(client):
    response = client.post("/auth/login", json={"email": "not-an-email", "password": "x"})
    assert response.status_code == 422


def test_me_requires_a_token(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_rejects_garbage_token(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_me_returns_the_logged_in_user(client, interviewer):
    headers = auth_headers(client, "interviewer@example.com")
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["role"] == UserRole.INTERVIEWER.value

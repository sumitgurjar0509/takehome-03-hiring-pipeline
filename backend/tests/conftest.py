"""
Test fixtures. Uses a real Postgres database (hiring_pipeline_test) rather
than mocking the ORM — this app has enough DB-enforced constraints (enums,
foreign keys, indexes) that a mock would hide real bugs. Every test runs
inside a transaction that's rolled back afterward, so tests don't leak
state into each other.
"""
import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg2://hiring_pipeline:devpassword@localhost:5432/hiring_pipeline_test",
)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth import hash_password
from app.database import Base, get_db
from app.main import app
from app.models import User, UserRole

TEST_DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield session
    session.close()
    transaction.rollback()
    connection.close()
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def client(db_session):
    return TestClient(app)


@pytest.fixture()
def make_user(db_session):
    """Factory fixture: make_user(email=..., role=..., password=...) -> User"""

    def _make_user(
        email: str,
        role: UserRole = UserRole.RECRUITER,
        password: str = "testpassword123",
        name: str = "Test User",
    ) -> User:
        user = User(
            email=email,
            name=name,
            role=role,
            password_hash=hash_password(password),
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _make_user


@pytest.fixture()
def recruiter(make_user):
    return make_user(email="recruiter@example.com", role=UserRole.RECRUITER)


@pytest.fixture()
def interviewer(make_user):
    return make_user(email="interviewer@example.com", role=UserRole.INTERVIEWER)


def auth_headers(client: TestClient, email: str, password: str = "testpassword123") -> dict:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

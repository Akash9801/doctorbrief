import os
import tempfile
from collections.abc import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.session import Base, get_db
from app.main import create_app


@pytest.fixture(scope="session")
def test_db_path() -> Generator[str, None, None]:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture(scope="function")
def db_session(test_db_path: str) -> Generator[Session, None, None]:
    engine = create_engine(
        f"sqlite:///{test_db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    app = create_app()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


def register_and_login(client: TestClient, email: str = "dr.sharma@clinic.in", full_name: str = "Dr. Ananya Sharma") -> dict:
    resp = client.post(
        "/api/auth/register",
        json={
            "full_name": full_name,
            "email": email,
            "password": "StrongPassword123!",
            "specialty": "General Medicine",
            "clinic_name": "Swasthya Care Clinic",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    return {
        "token": data["access_token"],
        "doctor": data["doctor"],
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
    }

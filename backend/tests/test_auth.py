from datetime import timedelta
from fastapi.testclient import TestClient

from app.security.auth import create_access_token
from tests.conftest import register_and_login


def test_register_login_and_profile(client: TestClient):
    auth = register_and_login(client)
    headers = auth["headers"]

    me_resp = client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "dr.sharma@clinic.in"

    # Duplicate email returns 409
    dup_resp = client.post(
        "/api/auth/register",
        json={
            "full_name": "Duplicate Doctor",
            "email": "dr.sharma@clinic.in",
            "password": "StrongPassword123!",
        },
    )
    assert dup_resp.status_code == 409

    # Login with valid credentials
    login_resp = client.post(
        "/api/auth/login",
        json={"email": "dr.sharma@clinic.in", "password": "StrongPassword123!"},
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()

    # Invalid password fails
    bad_login = client.post(
        "/api/auth/login",
        json={"email": "dr.sharma@clinic.in", "password": "WrongPassword"},
    )
    assert bad_login.status_code == 401

    # Profile update
    patch_resp = client.patch(
        "/api/auth/me",
        headers=headers,
        json={"clinic_name": "Indiranagar Health Clinic", "registration_number": "KMC-98412"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["clinic_name"] == "Indiranagar Health Clinic"
    assert patch_resp.json()["registration_number"] == "KMC-98412"


def test_protected_routes_require_valid_token(client: TestClient):
    unauth = client.get("/api/patients")
    assert unauth.status_code == 401

    expired_token = create_access_token("non-existent-id", expires_delta=timedelta(minutes=-5))
    expired_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert expired_resp.status_code == 401

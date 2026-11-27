from fastapi.testclient import TestClient
from tests.conftest import register_and_login


def test_patient_crud_and_ownership(client: TestClient):
    doc1 = register_and_login(client, email="doc1@clinic.in", full_name="Dr. First")
    doc2 = register_and_login(client, email="doc2@clinic.in", full_name="Dr. Second")

    # Create patient for doc1
    create_resp = client.post(
        "/api/patients",
        headers=doc1["headers"],
        json={
            "full_name": "Rohan Verma",
            "age": 34,
            "gender": "Male",
            "phone": "+91 9876543210",
            "medical_history": "Mild asthma",
            "allergies": "Penicillin",
        },
    )
    assert create_resp.status_code == 201
    patient = create_resp.json()
    assert patient["patient_code"] == "DB-0001"
    assert patient["full_name"] == "Rohan Verma"

    # List & search patients
    list_resp = client.get("/api/patients?search=Rohan", headers=doc1["headers"])
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # Update patient
    patch_resp = client.patch(
        f"/api/patients/{patient['id']}",
        headers=doc1["headers"],
        json={"allergies": "Penicillin, Sulfa drugs"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["allergies"] == "Penicillin, Sulfa drugs"

    # Ownership check: doc2 cannot read, update, or delete doc1's patient
    for method in ("get", "patch", "delete"):
        kwargs = {"headers": doc2["headers"]}
        if method == "patch":
            kwargs["json"] = {"full_name": "Hacked"}
        resp = getattr(client, method)(f"/api/patients/{patient['id']}", **kwargs)
        assert resp.status_code == 403

    # Doc2 list is empty
    doc2_list = client.get("/api/patients", headers=doc2["headers"])
    assert doc2_list.status_code == 200
    assert doc2_list.json() == []

    # Delete by owner works
    del_resp = client.delete(f"/api/patients/{patient['id']}", headers=doc1["headers"])
    assert del_resp.status_code == 204
    assert client.get(f"/api/patients/{patient['id']}", headers=doc1["headers"]).status_code == 404

from unittest.mock import patch
from fastapi.testclient import TestClient

from app.ai.client import ExtractionResult, SoapResult, TranscriptionResult
from app.schemas.extraction import ClinicalExtractionPayload
from app.schemas.note import SoapNoteDraft
from tests.conftest import register_and_login


def test_soap_note_edit_approve_amendment_and_history(client: TestClient):
    doc = register_and_login(client)
    p_resp = client.post(
        "/api/patients",
        headers=doc["headers"],
        json={
            "full_name": "Arjun Mehta",
            "age": 55,
            "gender": "Male",
            "phone": "+91 9900112233",
        },
    )
    patient_id = p_resp.json()["id"]

    c_resp = client.post(
        "/api/consultations",
        headers=doc["headers"],
        json={"patient_id": patient_id, "consent_status": "GRANTED"},
    )
    cid = c_resp.json()["id"]

    with (
        patch(
            "app.services.consultation_service.transcribe_audio_bytes",
            return_value=TranscriptionResult(text="BP 140/90 noted. Continue Amlodipine 5mg.", language="en"),
        ),
        patch(
            "app.services.consultation_service.extract_clinical_information",
            return_value=ExtractionResult(
                payload=ClinicalExtractionPayload(
                    chief_complaint="Hypertension follow-up",
                    vitals={"BP": "140/90 mmHg"},
                    assessment=["Essential hypertension"],
                    medication_instructions=["Continue Amlodipine 5mg OD"],
                ),
                model_name="gpt-4o-mini",
            ),
        ),
        patch(
            "app.services.consultation_service.generate_soap_note_draft",
            return_value=SoapResult(
                draft=SoapNoteDraft(
                    subjective="Follow-up visit for hypertension.",
                    objective="BP: 140/90 mmHg.",
                    assessment="Essential hypertension.",
                    plan="Continue Amlodipine 5mg once daily.",
                ),
                model_name="gpt-4o-mini",
            ),
        ),
    ):
        client.post(
            f"/api/consultations/{cid}/transcribe",
            headers=doc["headers"],
            files={"file": ("audio.webm", b"binary", "audio/webm")},
        )
        note = client.post(f"/api/consultations/{cid}/generate-note", headers=doc["headers"]).json()

    # Edit draft -> transitions to UNDER_REVIEW
    edit_resp = client.patch(
        f"/api/notes/{note['id']}",
        headers=doc["headers"],
        json={"plan": "Continue Amlodipine 5mg OD. Low salt diet. Review in 4 weeks."},
    )
    assert edit_resp.status_code == 200
    assert edit_resp.json()["status"] == "UNDER_REVIEW"

    # Dashboard shows 1 note awaiting approval
    dash_before = client.get("/api/dashboard", headers=doc["headers"]).json()
    assert dash_before["stats"]["notes_awaiting_approval"] == 1

    # Approve note
    approve_resp = client.post(
        f"/api/notes/{note['id']}/approve",
        headers=doc["headers"],
        json={"confirm_accuracy": True},
    )
    assert approve_resp.status_code == 200
    approved = approve_resp.json()
    assert approved["status"] == "APPROVED"
    assert approved["approved_by"] == doc["doctor"]["id"]
    assert approved["approved_at"] is not None

    # Direct edit to approved note is blocked (409 Conflict)
    blocked_edit = client.patch(
        f"/api/notes/{note['id']}",
        headers=doc["headers"],
        json={"plan": "Silent overwrite attempt"},
    )
    assert blocked_edit.status_code == 409

    # Creating an amendment creates version 2 in DRAFT, preserving version 1 APPROVED
    amend_resp = client.post(
        f"/api/notes/{note['id']}/amend",
        headers=doc["headers"],
        json={
            "subjective": approved["subjective"],
            "objective": approved["objective"],
            "assessment": approved["assessment"],
            "plan": approved["plan"] + " Added home BP log.",
            "amendment_reason": "Clarified home BP monitoring advice",
        },
    )
    assert amend_resp.status_code == 200
    v2 = amend_resp.json()
    assert v2["version"] == 2
    assert v2["status"] == "DRAFT"
    assert v2["parent_note_id"] == note["id"]

    # Patient history returns consultation with both versions
    hist_resp = client.get(f"/api/patients/{patient_id}/history", headers=doc["headers"])
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert len(history) == 1
    assert len(history[0]["note_versions"]) == 2

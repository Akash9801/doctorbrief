from unittest.mock import patch
from fastapi.testclient import TestClient

from app.ai.client import ExtractionResult, SoapResult, TranscriptionResult
from app.schemas.extraction import ClinicalExtractionPayload
from app.schemas.note import SoapNoteDraft
from tests.conftest import register_and_login


def _create_patient(client: TestClient, headers: dict) -> dict:
    resp = client.post(
        "/api/patients",
        headers=headers,
        json={
            "full_name": "Meera Nair",
            "age": 42,
            "gender": "Female",
            "phone": "+91 9811122233",
        },
    )
    assert resp.status_code == 201
    return resp.json()


def test_audio_upload_validation_and_consent_gate(client: TestClient):
    doc = register_and_login(client)
    patient = _create_patient(client, doc["headers"])

    # Create consultation without consent
    c_resp = client.post(
        "/api/consultations",
        headers=doc["headers"],
        json={"patient_id": patient["id"], "consent_status": "PENDING"},
    )
    assert c_resp.status_code == 201
    cid = c_resp.json()["id"]

    # Attempting transcribe without consent fails with 400
    no_consent = client.post(
        f"/api/consultations/{cid}/transcribe",
        headers=doc["headers"],
        files={"file": ("consult.webm", b"fake-audio-bytes", "audio/webm")},
    )
    assert no_consent.status_code == 400

    # Grant consent
    consent_resp = client.patch(
        f"/api/consultations/{cid}",
        headers=doc["headers"],
        json={"consent_status": "GRANTED"},
    )
    assert consent_resp.status_code == 200
    assert consent_resp.json()["consent_status"] == "GRANTED"

    # Empty audio fails with 400
    empty_resp = client.post(
        f"/api/consultations/{cid}/transcribe",
        headers=doc["headers"],
        files={"file": ("consult.webm", b"", "audio/webm")},
    )
    assert empty_resp.status_code == 400

    # Unsupported format fails with 415
    bad_fmt = client.post(
        f"/api/consultations/{cid}/transcribe",
        headers=doc["headers"],
        files={"file": ("notes.txt", b"plain text", "text/plain")},
    )
    assert bad_fmt.status_code == 415


def test_full_voice_to_soap_pipeline_with_mocked_openai(client: TestClient):
    doc1 = register_and_login(client, email="doc1@clinic.in")
    doc2 = register_and_login(client, email="doc2@clinic.in")
    patient = _create_patient(client, doc1["headers"])

    c_resp = client.post(
        "/api/consultations",
        headers=doc1["headers"],
        json={"patient_id": patient["id"], "consent_status": "GRANTED"},
    )
    assert c_resp.status_code == 201
    cid = c_resp.json()["id"]

    mock_transcript = TranscriptionResult(
        text="Patient reports fever and dry cough for 2 days. Doctor notes temp 100.2 F, chest clear. Assessment: viral fever. Plan: Paracetamol 500mg SOS and hydration.",
        language="en",
        is_mock=False,
    )
    mock_extraction = ExtractionResult(
        payload=ClinicalExtractionPayload(
            chief_complaint="Fever and dry cough",
            symptoms=["Fever", "Dry cough"],
            symptom_duration="2 days",
            vitals={"Temperature": "100.2 F"},
            examination_findings=["Chest clear"],
            assessment=["Viral fever (doctor stated)"],
            medication_instructions=["Paracetamol 500mg SOS"],
            plan=["Oral hydration"],
            missing_information=["Allergies not mentioned or asked"],
        ),
        model_name="gpt-4o-mini",
        is_mock=False,
    )
    mock_soap = SoapResult(
        draft=SoapNoteDraft(
            subjective="Chief complaint: Fever and dry cough for 2 days.",
            objective="Temperature: 100.2 F. Chest clear on examination.",
            assessment="Viral fever.",
            plan="Paracetamol 500mg SOS; maintain oral hydration.",
        ),
        model_name="gpt-4o-mini",
        is_mock=False,
    )

    with (
        patch("app.services.consultation_service.transcribe_audio_bytes", return_value=mock_transcript),
        patch("app.services.consultation_service.extract_clinical_information", return_value=mock_extraction),
        patch("app.services.consultation_service.generate_soap_note_draft", return_value=mock_soap),
    ):
        t_resp = client.post(
            f"/api/consultations/{cid}/transcribe",
            headers=doc1["headers"],
            files={"file": ("visit.webm", b"webm-audio-binary", "audio/webm")},
            data={"duration_seconds": "45"},
        )
        assert t_resp.status_code == 200
        assert "dry cough" in t_resp.json()["original_text"]

        # Doctor edits transcript while original_text remains intact
        edit_t = client.patch(
            f"/api/consultations/{cid}/transcript",
            headers=doc1["headers"],
            json={"edited_text": mock_transcript.text + " Review in 3 days."},
        )
        assert edit_t.status_code == 200
        assert edit_t.json()["original_text"] == mock_transcript.text
        assert "Review in 3 days" in edit_t.json()["edited_text"]

        # Extract clinical info
        ex_resp = client.post(f"/api/consultations/{cid}/extract", headers=doc1["headers"])
        assert ex_resp.status_code == 200
        assert ex_resp.json()["extracted_data"]["chief_complaint"] == "Fever and dry cough"

        # Generate SOAP note (must be DRAFT)
        note_resp = client.post(f"/api/consultations/{cid}/generate-note", headers=doc1["headers"])
        assert note_resp.status_code == 200
        note = note_resp.json()
        assert note["status"] == "DRAFT"
        assert note["version"] == 1

    # Ownership check on consultation and note
    assert client.get(f"/api/consultations/{cid}", headers=doc2["headers"]).status_code == 403
    assert client.post(f"/api/notes/{note['id']}/approve", headers=doc2["headers"]).status_code == 403

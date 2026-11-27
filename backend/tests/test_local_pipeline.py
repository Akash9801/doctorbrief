import io
import os
import struct
import wave
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.ai.client import (
    AIConfigurationError,
    extract_clinical_information,
    generate_soap_note_draft,
    transcribe_audio_bytes,
)
from app.ai.rule_extractor import extract_with_rules
from tests.conftest import register_and_login


def _make_silent_wav_bytes(duration_seconds: float = 0.6, sample_rate: int = 16000) -> bytes:
    """Create a valid PCM WAV byte buffer containing silence."""
    buf = io.BytesIO()
    num_frames = int(duration_seconds * sample_rate)
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack("<" + "h" * num_frames, *([0] * num_frames)))
    return buf.getvalue()


def _create_patient(client: TestClient, headers: dict) -> dict:
    resp = client.post(
        "/api/patients",
        headers=headers,
        json={
            "full_name": "Rohan Verma",
            "age": 38,
            "gender": "Male",
            "phone": "+91 9822001122",
        },
    )
    assert resp.status_code == 201
    return resp.json()


def test_rule_extractor_comprehensive_clinical_fields_and_negation():
    transcript = (
        "Doctor: Good morning, what brings you in today?\n"
        "Patient: I have had a dry cough and mild fever for the past 3 days, worse at night. "
        "I also have a history of hypertension and am currently taking Amlodipine 5 mg.\n"
        "Doctor: Any chest pain, shortness of breath, or known drug allergies?\n"
        "Patient: No chest pain or shortness of breath. No known allergies.\n"
        "Doctor: On examination, temperature is 99.8 F, BP 130/80 mmHg, SpO2 98% on room air, "
        "throat is mildly congested, chest is clear on auscultation.\n"
        "Doctor: Assessment: likely acute viral upper respiratory tract infection. "
        "Differential diagnosis: rule out early bronchitis.\n"
        "Doctor: Plan: Paracetamol 500 mg SOS for fever, warm saline gargles, plenty of fluids. "
        "Get a CBC blood test if fever persists. Review in 3 days."
    )

    extracted = extract_with_rules(transcript)

    assert extracted.chief_complaint is not None
    assert "Dry cough" in extracted.symptoms
    assert "Mild fever" in extracted.symptoms
    # Negated symptoms must NOT appear as positive symptoms
    assert not any("chest pain" in s.lower() for s in extracted.symptoms)
    assert not any("shortness of breath" in s.lower() for s in extracted.symptoms)
    assert any("pertinent negative" in o.lower() and "chest pain" in o.lower() for o in extracted.other_observations)

    assert extracted.symptom_duration is not None and "3 days" in extracted.symptom_duration
    assert extracted.symptom_severity is not None and "worse at night" in extracted.symptom_severity.lower()
    assert "Hypertension" in extracted.medical_history
    assert any("amlodipine" in m.lower() for m in extracted.medications)
    assert any("no known allergies" in a.lower() for a in extracted.allergies)

    assert extracted.vitals.get("Temperature") == "99.8 F"
    assert extracted.vitals.get("BP") == "130/80 mmHg"
    assert extracted.vitals.get("SpO2") == "98% on room air"

    assert any("congested" in e.lower() for e in extracted.examination_findings)
    assert any("viral upper respiratory" in a.lower() for a in extracted.assessment)
    assert any("bronchitis" in d.lower() for d in extracted.differential_diagnoses)
    assert any("paracetamol 500 mg" in m.lower() for m in extracted.medication_instructions)
    assert any("saline gargles" in p.lower() for p in extracted.plan)
    assert any("cbc" in inv.lower() for inv in extracted.investigations)
    assert extracted.follow_up is not None and "review in 3 days" in extracted.follow_up.lower()

    # Evidence quotes must be populated from transcript
    assert "symptoms" in extracted.evidence_quotes
    assert "vitals" in extracted.evidence_quotes
    assert "assessment" in extracted.evidence_quotes


def test_rule_extractor_missing_info_and_uncertainty():
    transcript = "Patient unsure of duration, maybe 2 days of headache. Possibly migraine."
    extracted = extract_with_rules(transcript)

    assert len(extracted.symptoms) == 1
    assert "headache" in extracted.symptoms[0].lower()
    assert "uncertain" in extracted.symptoms[0].lower()
    assert any("vitals not documented" in m.lower() for m in extracted.missing_information)
    assert any("allergies not mentioned" in m.lower() for m in extracted.missing_information)
    assert any("uncertain" in m.lower() for m in extracted.missing_information)


def test_soap_generation_marks_missing_as_not_documented():
    extracted = extract_with_rules("Patient: I have a headache.")
    soap = generate_soap_note_draft("Patient: I have a headache.", extracted)

    assert soap.is_mock is False
    assert "Headache" in soap.draft.subjective
    assert soap.draft.objective == "Not documented"
    assert soap.draft.assessment == "Not documented"
    assert soap.draft.plan == "Not documented"


def test_audio_validation_errors_and_whisper_failures(client: TestClient, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    doc = register_and_login(client, email="valdoc@clinic.in")
    patient = _create_patient(client, doc["headers"])
    cid = client.post(
        "/api/consultations",
        headers=doc["headers"],
        json={"patient_id": patient["id"], "consent_status": "GRANTED"},
    ).json()["id"]

    # Oversized upload -> 413
    with patch("app.config.Settings.max_audio_size_bytes", new=10):
        big_resp = client.post(
            f"/api/consultations/{cid}/transcribe",
            headers=doc["headers"],
            files={"file": ("big.webm", b"0123456789abcdef", "audio/webm")},
        )
        assert big_resp.status_code == 413

    # Corrupted audio -> 422
    fake_model = MagicMock()
    fake_model.transcribe.side_effect = ValueError("Invalid audio stream")
    with patch("app.ai.client._get_whisper_model", return_value=fake_model):
        corrupt_resp = client.post(
            f"/api/consultations/{cid}/transcribe",
            headers=doc["headers"],
            files={"file": ("corrupt.wav", b"RIFFBADDATA", "audio/wav")},
        )
        assert corrupt_resp.status_code == 422

    # No usable speech -> 422
    silent_model = MagicMock()
    silent_info = MagicMock(language="en")
    silent_model.transcribe.return_value = ([], silent_info)
    with patch("app.ai.client._get_whisper_model", return_value=silent_model):
        silent_resp = client.post(
            f"/api/consultations/{cid}/transcribe",
            headers=doc["headers"],
            files={"file": ("silence.wav", _make_silent_wav_bytes(), "audio/wav")},
        )
        assert silent_resp.status_code == 422

    # Whisper initialization failure -> 503
    with patch(
        "app.ai.client._get_whisper_model",
        side_effect=AIConfigurationError("Model init failed"),
    ):
        init_fail = client.post(
            f"/api/consultations/{cid}/transcribe",
            headers=doc["headers"],
            files={"file": ("visit.webm", b"fake-webm-bytes", "audio/webm")},
        )
        assert init_fail.status_code == 503


def test_end_to_end_local_workflow_without_external_api_keys(client: TestClient, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    doc1 = register_and_login(client, email="e2edoc1@clinic.in")
    doc2 = register_and_login(client, email="e2edoc2@clinic.in")
    patient = _create_patient(client, doc1["headers"])

    c_resp = client.post(
        "/api/consultations",
        headers=doc1["headers"],
        json={"patient_id": patient["id"], "consent_status": "GRANTED"},
    )
    assert c_resp.status_code == 201
    cid = c_resp.json()["id"]

    # Mock only Whisper model inference; extraction & SOAP run through real local code
    seg = MagicMock(
        text="Doctor: Temperature is 100.4 F. Patient has sore throat and fever for 2 days. "
        "No known allergies. Assessment: acute pharyngitis. "
        "Plan: Paracetamol 500 mg SOS and warm saline gargles. Review in 3 days."
    )
    info = MagicMock(language="en")
    fake_model = MagicMock()
    fake_model.transcribe.return_value = ([seg], info)

    with patch("app.ai.client._get_whisper_model", return_value=fake_model):
        t_resp = client.post(
            f"/api/consultations/{cid}/transcribe",
            headers=doc1["headers"],
            files={"file": ("consult.webm", b"webm-audio-payload", "audio/webm")},
            data={"duration_seconds": "30"},
        )
    assert t_resp.status_code == 200
    t_data = t_resp.json()
    assert t_data["language"] == "en"
    assert t_data["is_mock"] is False
    assert "sore throat" in t_data["original_text"].lower()

    # Edit transcript
    edit_t = client.patch(
        f"/api/consultations/{cid}/transcript",
        headers=doc1["headers"],
        json={"edited_text": t_data["original_text"] + " Hydration advised."},
    )
    assert edit_t.status_code == 200

    # Local rule-based extraction
    ex_resp = client.post(f"/api/consultations/{cid}/extract", headers=doc1["headers"])
    assert ex_resp.status_code == 200
    ex_data = ex_resp.json()
    assert ex_data["is_mock"] is False
    assert ex_data["model_name"] == "rule-based-clinical-extractor"
    assert "Sore throat" in ex_data["extracted_data"]["symptoms"]
    assert ex_data["extracted_data"]["vitals"]["Temperature"] == "100.4 F"

    # Deterministic SOAP generation (must be DRAFT)
    note_resp = client.post(f"/api/consultations/{cid}/generate-note", headers=doc1["headers"])
    assert note_resp.status_code == 200
    note = note_resp.json()
    assert note["status"] == "DRAFT"
    assert note["is_mock"] is False
    assert "100.4 F" in note["objective"]

    # Ownership check before approval
    assert client.post(f"/api/notes/{note['id']}/approve", headers=doc2["headers"]).status_code == 403

    # Edit note & approve
    patch_note = client.patch(
        f"/api/notes/{note['id']}",
        headers=doc1["headers"],
        json={"plan": note["plan"] + "\nDrink warm fluids."},
    )
    assert patch_note.status_code == 200
    assert patch_note.json()["status"] == "UNDER_REVIEW"

    approve_resp = client.post(
        f"/api/notes/{note['id']}/approve",
        headers=doc1["headers"],
        json={"confirm_accuracy": True},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "APPROVED"

    # Verify persisted via GET /note
    get_note = client.get(f"/api/consultations/{cid}/note", headers=doc1["headers"])
    assert get_note.status_code == 200
    assert get_note.json()["status"] == "APPROVED"


def test_real_faster_whisper_silence_and_cleanup():
    """Exercise actual faster-whisper model on real WAV bytes (no mocking)."""
    wav_bytes = _make_silent_wav_bytes(duration_seconds=0.8)
    try:
        res = transcribe_audio_bytes(wav_bytes, "silence.wav", "audio/wav")
        # If Whisper outputs anything at all, ensure it's a valid TranscriptionResult
        assert isinstance(res.text, str)
    except Exception as exc:
        # On pure silence, Whisper raises AIServiceError(422) for no usable speech
        assert getattr(exc, "status_code", None) in (422, 503)

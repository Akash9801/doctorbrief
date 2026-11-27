import io
import json
import logging
from dataclasses import dataclass
from typing import Any

from groq import Groq, APIConnectionError, APIStatusError, APITimeoutError
from openai import OpenAI, OpenAIError
from pydantic import ValidationError

from app.ai.prompts import EXTRACTION_SYSTEM_PROMPT, SOAP_SYSTEM_PROMPT
from app.config import get_settings
from app.schemas.extraction import ClinicalExtractionPayload
from app.schemas.note import SoapNoteDraft

logger = logging.getLogger("doctorbrief.ai")

# Audio formats supported by Groq Whisper
GROQ_SUPPORTED_EXTENSIONS = {".webm", ".wav", ".mp3", ".m4a", ".mp4", ".mpeg", ".mpga", ".ogg", ".oga", ".flac"}
GROQ_SUPPORTED_CONTENT_TYPES = {
    "audio/webm", "video/webm",
    "audio/wav", "audio/x-wav", "audio/wave",
    "audio/mpeg", "audio/mp3",
    "audio/mp4", "audio/m4a", "audio/x-m4a",
    "audio/ogg", "application/ogg", "audio/oga",
    "audio/flac", "audio/x-flac",
}


class AIServiceError(Exception):
    """Base error raised for AI processing failures."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AIConfigurationError(AIServiceError):
    """Raised when a required API key is missing."""

    def __init__(self, message: str):
        super().__init__(message, status_code=503)


@dataclass
class TranscriptionResult:
    text: str
    language: str | None
    is_mock: bool = False


@dataclass
class ExtractionResult:
    payload: ClinicalExtractionPayload
    model_name: str
    is_mock: bool = False


@dataclass
class SoapResult:
    draft: SoapNoteDraft
    model_name: str
    is_mock: bool = False


# ---------------------------------------------------------------------------
# Groq client (transcription)
# ---------------------------------------------------------------------------

def _get_groq_client() -> Groq | None:
    """Return a Groq client if GROQ_API_KEY is configured, None when mock is allowed."""
    settings = get_settings()
    api_key = (settings.GROQ_API_KEY or "").strip()
    if api_key and not api_key.startswith("your_groq"):
        return Groq(api_key=api_key, timeout=120.0)
    if settings.ALLOW_DEV_AI_MOCK:
        return None
    raise AIConfigurationError(
        "Groq API key is not configured. Set GROQ_API_KEY in the backend environment."
    )


# ---------------------------------------------------------------------------
# OpenAI client (clinical extraction + SOAP generation)
# ---------------------------------------------------------------------------

def _get_openai_client() -> OpenAI | None:
    """Return an OpenAI client if OPENAI_API_KEY is configured, None when mock is allowed."""
    settings = get_settings()
    api_key = (settings.OPENAI_API_KEY or "").strip()
    if api_key and not api_key.startswith("sk-your-"):
        return OpenAI(api_key=api_key, timeout=60.0)
    if settings.ALLOW_DEV_AI_MOCK:
        return None
    raise AIConfigurationError(
        "OpenAI API key is not configured. Set OPENAI_API_KEY on the backend server."
    )


# ---------------------------------------------------------------------------
# Transcription  — Groq Whisper Large V3 Turbo
# ---------------------------------------------------------------------------

def transcribe_audio_bytes(
    audio_bytes: bytes,
    filename: str,
    content_type: str | None = None,
) -> TranscriptionResult:
    """Transcribe consultation audio via Groq Whisper Large V3 Turbo."""
    client = _get_groq_client()

    if client is None:
        logger.info("Using development-only mock transcription adapter (ALLOW_DEV_AI_MOCK=true)")
        return TranscriptionResult(
            text=(
                "[DEVELOPMENT MOCK TRANSCRIPT - NO GROQ API KEY CONFIGURED]\n"
                "Doctor: Good morning, what brings you in today?\n"
                "Patient: I have had a dry cough and mild fever for the past 3 days, mostly worse at night.\n"
                "Doctor: Any shortness of breath, chest pain, or known drug allergies?\n"
                "Patient: No chest pain or breathing trouble. No known allergies.\n"
                "Doctor: On examination, temperature is 99.8 F, SpO2 98 percent on room air, throat is mildly congested, chest is clear.\n"
                "Doctor: Assessment is likely acute viral upper respiratory tract infection. Plan: Paracetamol 500 mg SOS for fever, warm saline gargles, plenty of fluids, and review in 3 days if fever persists."
            ),
            language="en",
            is_mock=True,
        )

    # Validate that the audio format is supported by Groq before sending
    lower_name = (filename or "").lower()
    ext_ok = any(lower_name.endswith(ext) for ext in GROQ_SUPPORTED_EXTENSIONS)
    normalized_ct = (content_type or "").split(";")[0].strip().lower()
    ct_ok = normalized_ct in GROQ_SUPPORTED_CONTENT_TYPES if normalized_ct else False
    if not ext_ok and not ct_ok:
        raise AIServiceError(
            "Unsupported audio format for transcription. Groq Whisper accepts WebM, WAV, MP3, M4A, MP4, OGG, and FLAC.",
            status_code=415,
        )

    effective_filename = filename or "consultation.webm"
    effective_content_type = normalized_ct or "audio/webm"

    try:
        response = client.audio.transcriptions.create(
            file=(effective_filename, audio_bytes, effective_content_type),
            model="whisper-large-v3-turbo",
            response_format="verbose_json",
            temperature=0.0,
        )
    except APITimeoutError as exc:
        logger.warning("Groq transcription timed out")
        raise AIServiceError(
            "Transcription request timed out. The audio file may be too long; please try a shorter recording.",
            status_code=504,
        ) from exc
    except APIConnectionError as exc:
        logger.warning("Groq transcription connection error: %s", type(exc).__name__)
        raise AIServiceError(
            "Could not reach the transcription service. Please check your connection and retry.",
            status_code=502,
        ) from exc
    except APIStatusError as exc:
        status_code = exc.status_code
        logger.warning("Groq transcription API error: HTTP %s", status_code)
        if status_code == 401:
            raise AIServiceError("Groq API key is invalid or unauthorised.", status_code=503) from exc
        if status_code == 429:
            raise AIServiceError(
                "Transcription service rate limit reached. Please wait a moment and retry.",
                status_code=429,
            ) from exc
        if status_code in (503, 529):
            raise AIServiceError(
                "Transcription service is temporarily unavailable. Please retry shortly.",
                status_code=503,
            ) from exc
        raise AIServiceError(
            "Speech-to-text transcription service failed. Please retry uploading the recording.",
            status_code=502,
        ) from exc

    text = getattr(response, "text", None)
    if text is None and isinstance(response, dict):
        text = response.get("text")
    text = (text or "").strip()

    if not text:
        raise AIServiceError(
            "Transcription returned empty text. Please verify the audio recording has audible speech.",
            status_code=422,
        )

    language = getattr(response, "language", None)
    return TranscriptionResult(text=text, language=language or "en", is_mock=False)



def _compute_missing_information(payload: ClinicalExtractionPayload) -> list[str]:
    missing = list(payload.missing_information)
    checks = [
        (not payload.vitals, "Vitals not documented"),
        (not payload.examination_findings, "Physical examination findings not documented"),
        (not payload.allergies, "Allergies not mentioned or asked"),
        (not payload.assessment, "Clinical assessment not explicitly documented"),
        (not payload.plan and not payload.medication_instructions, "Treatment plan not explicitly documented"),
        (not payload.follow_up, "Follow-up instructions not stated"),
    ]
    existing_lower = {item.lower() for item in missing}
    for condition, label in checks:
        if condition and label.lower() not in existing_lower:
            missing.append(label)
            existing_lower.add(label.lower())
    return missing


def extract_clinical_information(transcript_text: str) -> ExtractionResult:
    """Extract structured clinical information from a transcript using OpenAI structured outputs."""
    settings = get_settings()
    client = _get_openai_client()

    if client is None:
        logger.info("Using development-only mock extraction adapter (ALLOW_DEV_AI_MOCK=true)")
        mock_payload = _heuristic_dev_mock_extraction(transcript_text)
        mock_payload.missing_information = _compute_missing_information(mock_payload)
        return ExtractionResult(payload=mock_payload, model_name="dev-mock-extractor", is_mock=True)

    try:
        completion = client.beta.chat.completions.parse(
            model=settings.OPENAI_CLINICAL_MODEL,
            temperature=0,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Extract clinical facts strictly from the following consultation transcript:\n\n{transcript_text}",
                },
            ],
            response_format=ClinicalExtractionPayload,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raw_content = completion.choices[0].message.content or "{}"
            parsed = ClinicalExtractionPayload.model_validate_json(raw_content)
    except (OpenAIError, ValidationError, json.JSONDecodeError) as exc:
        logger.warning("Clinical extraction failed: %s", type(exc).__name__)
        raise AIServiceError(
            "Clinical information extraction failed. Your transcript is preserved; please retry.",
            status_code=502,
        ) from exc

    parsed.missing_information = _compute_missing_information(parsed)
    return ExtractionResult(
        payload=parsed,
        model_name=settings.OPENAI_CLINICAL_MODEL,
        is_mock=False,
    )


def generate_soap_note_draft(
    transcript_text: str,
    extracted: ClinicalExtractionPayload,
) -> SoapResult:
    """Generate a draft SOAP note strictly grounded in transcript and extracted facts."""
    settings = get_settings()
    client = _get_openai_client()

    if client is None:
        logger.info("Using development-only mock SOAP generator (ALLOW_DEV_AI_MOCK=true)")
        return SoapResult(
            draft=_build_grounded_soap_fallback(extracted),
            model_name="dev-mock-soap",
            is_mock=True,
        )

    extracted_json = extracted.model_dump_json(indent=2)
    user_prompt = (
        "Generate a structured SOAP note strictly from the transcript and extracted clinical data below.\n\n"
        f"EXTRACTED CLINICAL DATA:\n{extracted_json}\n\n"
        f"TRANSCRIPT:\n{transcript_text}"
    )

    try:
        completion = client.beta.chat.completions.parse(
            model=settings.OPENAI_CLINICAL_MODEL,
            temperature=0,
            messages=[
                {"role": "system", "content": SOAP_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format=SoapNoteDraft,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raw_content = completion.choices[0].message.content or "{}"
            parsed = SoapNoteDraft.model_validate_json(raw_content)
    except (OpenAIError, ValidationError, json.JSONDecodeError) as exc:
        logger.warning("SOAP note generation failed: %s", type(exc).__name__)
        raise AIServiceError(
            "SOAP note generation failed. Your transcript and extracted data are preserved; please retry.",
            status_code=502,
        ) from exc

    return SoapResult(
        draft=parsed,
        model_name=settings.OPENAI_CLINICAL_MODEL,
        is_mock=False,
    )


def _heuristic_dev_mock_extraction(transcript_text: str) -> ClinicalExtractionPayload:
    """Deterministic dev-only extraction used solely when ALLOW_DEV_AI_MOCK=true."""
    lower = transcript_text.lower()
    symptoms: list[str] = []
    for kw, label in [
        ("cough", "Dry cough"),
        ("fever", "Mild fever"),
        ("headache", "Headache"),
        ("sore throat", "Sore throat"),
        ("fatigue", "Fatigue"),
    ]:
        if kw in lower:
            symptoms.append(label)

    vitals: dict[str, str] = {}
    if "99.8" in lower:
        vitals["Temperature"] = "99.8 F"
    if "98 percent" in lower or "98%" in lower:
        vitals["SpO2"] = "98% on room air"

    exam: list[str] = []
    if "throat is mildly congested" in lower:
        exam.append("Mildly congested throat")
    if "chest is clear" in lower:
        exam.append("Chest clear on auscultation")

    assessment: list[str] = []
    if "viral upper respiratory" in lower:
        assessment.append("Acute viral upper respiratory tract infection (doctor stated)")

    plan: list[str] = []
    meds: list[str] = []
    if "paracetamol" in lower:
        meds.append("Paracetamol 500 mg SOS for fever (as stated by doctor)")
    if "saline gargles" in lower:
        plan.append("Warm saline gargles")
    if "fluids" in lower:
        plan.append("Adequate oral hydration")

    return ClinicalExtractionPayload(
        chief_complaint=symptoms[0] if symptoms else "Reported during consultation (dev mock)",
        symptoms=symptoms,
        symptom_duration="3 days" if "3 days" in lower else None,
        allergies=["No known allergies (patient stated)"] if "no known allergies" in lower else [],
        vitals=vitals,
        examination_findings=exam,
        assessment=assessment,
        plan=plan,
        medication_instructions=meds,
        follow_up="Review in 3 days if fever persists" if "3 days" in lower else None,
    )


def _build_grounded_soap_fallback(extracted: ClinicalExtractionPayload) -> SoapNoteDraft:
    s_parts: list[str] = []
    if extracted.chief_complaint:
        s_parts.append(f"Chief Complaint: {extracted.chief_complaint}")
    if extracted.symptoms:
        s_parts.append(f"Symptoms: {', '.join(extracted.symptoms)}")
    if extracted.symptom_duration:
        s_parts.append(f"Duration: {extracted.symptom_duration}")
    if extracted.symptom_severity:
        s_parts.append(f"Severity: {extracted.symptom_severity}")
    if extracted.medical_history:
        s_parts.append(f"Relevant Medical History: {', '.join(extracted.medical_history)}")
    if extracted.medications:
        s_parts.append(f"Current Medications: {', '.join(extracted.medications)}")
    if extracted.allergies:
        s_parts.append(f"Allergies: {', '.join(extracted.allergies)}")

    o_parts: list[str] = []
    if extracted.vitals:
        vitals_str = "; ".join(f"{k}: {v}" for k, v in extracted.vitals.items())
        o_parts.append(f"Vitals: {vitals_str}")
    if extracted.examination_findings:
        o_parts.append(f"Physical Examination: {'; '.join(extracted.examination_findings)}")
    if extracted.other_observations:
        o_parts.append(f"Observations: {'; '.join(extracted.other_observations)}")

    a_parts: list[str] = []
    if extracted.assessment:
        a_parts.append("; ".join(extracted.assessment))
    if extracted.differential_diagnoses:
        a_parts.append(f"Differential Diagnoses: {', '.join(extracted.differential_diagnoses)}")

    p_parts: list[str] = []
    if extracted.medication_instructions:
        p_parts.append(f"Medications Discussed: {'; '.join(extracted.medication_instructions)}")
    if extracted.plan:
        p_parts.append(f"Care Plan: {'; '.join(extracted.plan)}")
    if extracted.investigations:
        p_parts.append(f"Investigations: {', '.join(extracted.investigations)}")
    if extracted.follow_up:
        p_parts.append(f"Follow-up: {extracted.follow_up}")

    return SoapNoteDraft(
        subjective="\n".join(s_parts) if s_parts else "No subjective symptoms were documented in the transcript.",
        objective="\n".join(o_parts) if o_parts else "No vitals or physical examination findings were documented during this consultation.",
        assessment="\n".join(a_parts) if a_parts else "Clinical assessment was not explicitly documented in the transcript.",
        plan="\n".join(p_parts) if p_parts else "Treatment plan and follow-up instructions were not explicitly documented in the transcript.",
    )

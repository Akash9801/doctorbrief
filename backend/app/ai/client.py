import logging
import os
import tempfile
import threading
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from app.ai.rule_extractor import extract_with_rules
from app.config import get_settings
from app.schemas.extraction import ClinicalExtractionPayload
from app.schemas.note import SoapNoteDraft

logger = logging.getLogger("doctorbrief.ai")

SUPPORTED_AUDIO_EXTENSIONS = {".webm", ".wav", ".mp3", ".m4a", ".mp4", ".mpeg", ".mpga", ".ogg", ".oga", ".flac"}
SUPPORTED_AUDIO_CONTENT_TYPES = {
    "audio/webm",
    "video/webm",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/ogg",
    "application/ogg",
    "audio/oga",
    "audio/flac",
    "audio/x-flac",
}

_CONTENT_TYPE_TO_EXT = {
    "audio/webm": ".webm",
    "video/webm": ".webm",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/wave": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/mp4": ".mp4",
    "audio/m4a": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/ogg": ".ogg",
    "application/ogg": ".ogg",
    "audio/oga": ".oga",
    "audio/flac": ".flac",
    "audio/x-flac": ".flac",
}


class AIServiceError(Exception):
    """Base error raised for local AI processing failures."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AIConfigurationError(AIServiceError):
    """Raised when local model configuration or initialization fails."""

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
# Local Whisper model singleton (faster-whisper)
# ---------------------------------------------------------------------------

_whisper_model_lock = threading.Lock()
_whisper_model: Any = None
_whisper_model_key: tuple[str, str, str] | None = None


def _get_whisper_model() -> Any:
    """Load the faster-whisper model once and reuse it across requests."""
    global _whisper_model, _whisper_model_key
    settings = get_settings()
    key = (
        settings.WHISPER_MODEL_SIZE,
        settings.WHISPER_DEVICE,
        settings.WHISPER_COMPUTE_TYPE,
    )
    if _whisper_model is not None and _whisper_model_key == key:
        return _whisper_model

    with _whisper_model_lock:
        if _whisper_model is not None and _whisper_model_key == key:
            return _whisper_model
        try:
            from faster_whisper import WhisperModel

            logger.info(
                "Initializing faster-whisper model=%s device=%s compute_type=%s",
                settings.WHISPER_MODEL_SIZE,
                settings.WHISPER_DEVICE,
                settings.WHISPER_COMPUTE_TYPE,
            )
            _whisper_model = WhisperModel(
                settings.WHISPER_MODEL_SIZE,
                device=settings.WHISPER_DEVICE,
                compute_type=settings.WHISPER_COMPUTE_TYPE,
            )
            _whisper_model_key = key
        except Exception as exc:
            logger.exception("Failed to initialize faster-whisper model")
            raise AIConfigurationError(
                "Local speech-to-text model failed to initialize. Please check server logs and retry."
            ) from exc
        return _whisper_model


def _resolve_audio_extension(filename: str, content_type: str | None) -> str:
    lower_name = (filename or "").lower().strip()
    for ext in SUPPORTED_AUDIO_EXTENSIONS:
        if lower_name.endswith(ext):
            return ext
    normalized_ct = (content_type or "").split(";")[0].strip().lower()
    if normalized_ct in _CONTENT_TYPE_TO_EXT:
        return _CONTENT_TYPE_TO_EXT[normalized_ct]
    return ".webm"


# ---------------------------------------------------------------------------
# Transcription — Local faster-whisper
# ---------------------------------------------------------------------------


def transcribe_audio_bytes(
    audio_bytes: bytes,
    filename: str,
    content_type: str | None = None,
) -> TranscriptionResult:
    """Transcribe consultation audio locally using faster-whisper."""
    if not audio_bytes:
        raise AIServiceError(
            "Uploaded audio file is empty. Please record audio before uploading.",
            status_code=400,
        )

    lower_name = (filename or "").lower()
    ext_ok = any(lower_name.endswith(ext) for ext in SUPPORTED_AUDIO_EXTENSIONS)
    normalized_ct = (content_type or "").split(";")[0].strip().lower()
    ct_ok = normalized_ct in SUPPORTED_AUDIO_CONTENT_TYPES if normalized_ct else False
    if not ext_ok and not ct_ok:
        raise AIServiceError(
            "Unsupported audio format for transcription. Supported formats: WebM, WAV, MP3, M4A, OGG, and FLAC.",
            status_code=415,
        )

    model = _get_whisper_model()
    ext = _resolve_audio_extension(filename, content_type)
    tmp_path: str | None = None

    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name

        segments, info = model.transcribe(tmp_path, beam_size=5)
        text_parts = [seg.text.strip() for seg in segments if getattr(seg, "text", None) and seg.text.strip()]
        text = " ".join(text_parts).strip()
        detected_language = getattr(info, "language", None) or "en"
    except AIServiceError:
        raise
    except (ValueError, EOFError, OSError, RuntimeError) as exc:
        logger.exception("Audio decoding or Whisper inference failed")
        raise AIServiceError(
            "Unable to decode or transcribe the audio file. The recording may be corrupted or invalid.",
            status_code=422,
        ) from exc
    except Exception as exc:
        # Catch PyAV / decoder errors without importing av directly at module top
        exc_name = type(exc).__name__
        logger.exception("Unexpected transcription error (%s)", exc_name)
        if "InvalidData" in exc_name or "FFmpeg" in exc_name or "Decoder" in exc_name:
            raise AIServiceError(
                "Corrupted or unreadable audio file. Please record again and retry.",
                status_code=422,
            ) from exc
        raise AIServiceError(
            "Speech-to-text transcription failed. Please retry uploading the recording.",
            status_code=500,
        ) from exc
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                logger.warning("Failed to clean up temporary audio file")

    if not text:
        raise AIServiceError(
            "No usable speech was detected in the audio recording. Please verify the microphone and retry.",
            status_code=422,
        )

    return TranscriptionResult(text=text, language=detected_language, is_mock=False)


# ---------------------------------------------------------------------------
# Clinical Extraction — Deterministic Python Rule Engine
# ---------------------------------------------------------------------------


def extract_clinical_information(transcript_text: str) -> ExtractionResult:
    """Extract structured clinical information from a transcript using deterministic rules."""
    cleaned = (transcript_text or "").strip()
    if not cleaned:
        raise AIServiceError(
            "Transcript is empty. Cannot extract clinical information.",
            status_code=422,
        )

    try:
        payload = extract_with_rules(cleaned)
        validated = ClinicalExtractionPayload.model_validate(payload.model_dump())
    except ValidationError as exc:
        logger.exception("Clinical extraction schema validation failed")
        raise AIServiceError(
            "Clinical information extraction failed validation.",
            status_code=422,
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error during clinical extraction")
        raise AIServiceError(
            "Clinical information extraction failed. Your transcript is preserved; please retry.",
            status_code=500,
        ) from exc

    return ExtractionResult(
        payload=validated,
        model_name="rule-based-clinical-extractor",
        is_mock=False,
    )


# ---------------------------------------------------------------------------
# SOAP Generation — Deterministic Grounded Templates
# ---------------------------------------------------------------------------


def _build_grounded_soap_fallback(extracted: ClinicalExtractionPayload) -> SoapNoteDraft:
    """Build a deterministic SOAP note strictly from extracted clinical facts."""
    s_parts: list[str] = []
    s_parts.append(f"Chief Complaint: {extracted.chief_complaint or 'Not documented'}")
    if extracted.symptoms:
        s_parts.append(f"Symptoms: {', '.join(extracted.symptoms)}")
    else:
        s_parts.append("Symptoms: Not documented")
    s_parts.append(f"Duration: {extracted.symptom_duration or 'Not documented'}")
    if extracted.symptom_severity:
        s_parts.append(f"Severity: {extracted.symptom_severity}")
    if extracted.medical_history:
        s_parts.append(f"Relevant Medical History: {', '.join(extracted.medical_history)}")
    if extracted.medications:
        s_parts.append(f"Current Medications: {', '.join(extracted.medications)}")
    s_parts.append(
        f"Allergies: {', '.join(extracted.allergies) if extracted.allergies else 'Not documented'}"
    )
    if extracted.lifestyle_info:
        s_parts.append(f"Lifestyle: {'; '.join(extracted.lifestyle_info)}")

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
        subjective="\n".join(s_parts) if any([extracted.chief_complaint, extracted.symptoms, extracted.medical_history, extracted.medications, extracted.allergies]) else "Not documented",
        objective="\n".join(o_parts) if o_parts else "Not documented",
        assessment="\n".join(a_parts) if a_parts else "Not documented",
        plan="\n".join(p_parts) if p_parts else "Not documented",
    )


def generate_soap_note_draft(
    transcript_text: str,
    extracted: ClinicalExtractionPayload,
) -> SoapResult:
    """Generate a draft SOAP note deterministically from extracted clinical facts."""
    if not (transcript_text or "").strip():
        raise AIServiceError(
            "Transcript is empty. Cannot generate SOAP note.",
            status_code=422,
        )

    try:
        draft = _build_grounded_soap_fallback(extracted)
    except Exception as exc:
        logger.exception("SOAP note template generation failed")
        raise AIServiceError(
            "SOAP note generation failed. Your transcript and extracted data are preserved; please retry.",
            status_code=500,
        ) from exc

    return SoapResult(
        draft=draft,
        model_name="deterministic-soap-template",
        is_mock=False,
    )

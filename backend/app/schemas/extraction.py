from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ClinicalExtractionPayload(BaseModel):
    """Structured clinical facts strictly grounded in the consultation transcript."""

    chief_complaint: str | None = Field(default=None, description="Primary reason for the visit stated by patient.")
    symptoms: list[str] = Field(default_factory=list, description="Patient-reported symptoms explicitly mentioned.")
    symptom_duration: str | None = Field(default=None, description="Duration of symptoms if stated.")
    symptom_severity: str | None = Field(default=None, description="Severity of symptoms if stated.")
    medical_history: list[str] = Field(default_factory=list, description="Relevant medical history explicitly mentioned.")
    medications: list[str] = Field(default_factory=list, description="Current or past medications explicitly stated.")
    allergies: list[str] = Field(default_factory=list, description="Allergies explicitly stated.")
    lifestyle_info: list[str] = Field(default_factory=list, description="Relevant lifestyle information explicitly stated.")
    vitals: dict[str, str] = Field(default_factory=dict, description="Vitals explicitly mentioned by doctor/patient.")
    examination_findings: list[str] = Field(default_factory=list, description="Physical examination findings explicitly stated by doctor.")
    other_observations: list[str] = Field(default_factory=list, description="Other clinical observations explicitly stated by doctor.")
    assessment: list[str] = Field(default_factory=list, description="Clinical assessment explicitly stated by doctor.")
    differential_diagnoses: list[str] = Field(default_factory=list, description="Differential diagnoses only if explicitly mentioned.")
    plan: list[str] = Field(default_factory=list, description="Treatment plan explicitly stated.")
    medication_instructions: list[str] = Field(default_factory=list, description="Medication instructions explicitly stated by doctor.")
    investigations: list[str] = Field(default_factory=list, description="Investigations recommended by doctor.")
    follow_up: str | None = Field(default=None, description="Follow-up instructions explicitly stated.")
    missing_information: list[str] = Field(
        default_factory=list,
        description="Important clinical areas not documented or unclear in the transcript.",
    )
    evidence_quotes: dict[str, str] = Field(
        default_factory=dict,
        description="Short verbatim transcript snippets supporting key extracted items.",
    )


class ClinicalExtractionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    consultation_id: str
    extracted_data: dict[str, Any]
    missing_information: list[str]
    model_name: str | None = None
    is_mock: bool = False
    created_at: datetime
    updated_at: datetime

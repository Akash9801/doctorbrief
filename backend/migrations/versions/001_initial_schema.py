"""initial schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-11-27
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "doctors",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("specialty", sa.String(length=150), nullable=True),
        sa.Column("clinic_name", sa.String(length=200), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("registration_number", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_doctors_email", "doctors", ["email"], unique=True)

    op.create_table(
        "patients",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("doctor_id", sa.String(length=36), nullable=False),
        sa.Column("patient_code", sa.String(length=32), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("gender", sa.String(length=32), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=False),
        sa.Column("medical_history", sa.Text(), nullable=True),
        sa.Column("allergies", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("doctor_id", "patient_code", name="uq_doctor_patient_code"),
    )
    op.create_index("ix_patients_doctor_id", "patients", ["doctor_id"], unique=False)
    op.create_index("ix_patients_doctor_name", "patients", ["doctor_id", "full_name"], unique=False)
    op.create_index("ix_patients_patient_code", "patients", ["patient_code"], unique=False)

    op.create_table(
        "consultations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("doctor_id", sa.String(length=36), nullable=False),
        sa.Column("patient_id", sa.String(length=36), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("consent_status", sa.String(length=32), nullable=False),
        sa.Column("consent_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("audio_filename", sa.String(length=255), nullable=True),
        sa.Column("audio_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_consultations_doctor_created", "consultations", ["doctor_id", "created_at"], unique=False)
    op.create_index("ix_consultations_doctor_id", "consultations", ["doctor_id"], unique=False)
    op.create_index("ix_consultations_patient_created", "consultations", ["patient_id", "created_at"], unique=False)
    op.create_index("ix_consultations_patient_id", "consultations", ["patient_id"], unique=False)

    op.create_table(
        "transcripts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("consultation_id", sa.String(length=36), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("edited_text", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=32), nullable=True),
        sa.Column("processing_status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("is_mock", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["consultation_id"], ["consultations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transcripts_consultation_id", "transcripts", ["consultation_id"], unique=True)

    op.create_table(
        "clinical_extractions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("consultation_id", sa.String(length=36), nullable=False),
        sa.Column("extracted_data", sa.JSON(), nullable=False),
        sa.Column("missing_information", sa.JSON(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("is_mock", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["consultation_id"], ["consultations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clinical_extractions_consultation_id", "clinical_extractions", ["consultation_id"], unique=True)

    op.create_table(
        "clinical_notes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("consultation_id", sa.String(length=36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("subjective", sa.Text(), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("assessment", sa.Text(), nullable=False),
        sa.Column("plan", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("amendment_reason", sa.Text(), nullable=True),
        sa.Column("parent_note_id", sa.String(length=36), nullable=True),
        sa.Column("approved_by", sa.String(length=36), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_mock", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["approved_by"], ["doctors.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["consultation_id"], ["consultations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_note_id"], ["clinical_notes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clinical_notes_consultation_id", "clinical_notes", ["consultation_id"], unique=False)
    op.create_index("ix_clinical_notes_consultation_version", "clinical_notes", ["consultation_id", "version"], unique=False)
    op.create_index("ix_clinical_notes_status", "clinical_notes", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_clinical_notes_status", table_name="clinical_notes")
    op.drop_index("ix_clinical_notes_consultation_version", table_name="clinical_notes")
    op.drop_index("ix_clinical_notes_consultation_id", table_name="clinical_notes")
    op.drop_table("clinical_notes")
    op.drop_index("ix_clinical_extractions_consultation_id", table_name="clinical_extractions")
    op.drop_table("clinical_extractions")
    op.drop_index("ix_transcripts_consultation_id", table_name="transcripts")
    op.drop_table("transcripts")
    op.drop_index("ix_consultations_patient_id", table_name="consultations")
    op.drop_index("ix_consultations_patient_created", table_name="consultations")
    op.drop_index("ix_consultations_doctor_id", table_name="consultations")
    op.drop_index("ix_consultations_doctor_created", table_name="consultations")
    op.drop_table("consultations")
    op.drop_index("ix_patients_patient_code", table_name="patients")
    op.drop_index("ix_patients_doctor_name", table_name="patients")
    op.drop_index("ix_patients_doctor_id", table_name="patients")
    op.drop_table("patients")
    op.drop_index("ix_doctors_email", table_name="doctors")
    op.drop_table("doctors")

export interface Doctor {
  id: string;
  full_name: string;
  email: string;
  specialty?: string | null;
  clinic_name?: string | null;
  phone?: string | null;
  registration_number?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  doctor: Doctor;
}

export interface Patient {
  id: string;
  doctor_id: string;
  patient_code: string;
  full_name: string;
  date_of_birth?: string | null;
  age?: number | null;
  gender: string;
  phone: string;
  medical_history?: string | null;
  allergies?: string | null;
  created_at: string;
  updated_at: string;
  consultation_count: number;
}

export interface Transcript {
  id: string;
  consultation_id: string;
  original_text: string;
  edited_text?: string | null;
  language?: string | null;
  processing_status: string;
  error_message?: string | null;
  is_mock: boolean;
  created_at: string;
  updated_at: string;
}

export interface ClinicalExtractionData {
  chief_complaint: string | null;
  symptoms: string[];
  symptom_duration: string | null;
  symptom_severity: string | null;
  medical_history: string[];
  medications: string[];
  allergies: string[];
  lifestyle_info: string[];
  vitals: Record<string, string>;
  examination_findings: string[];
  other_observations: string[];
  assessment: string[];
  differential_diagnoses: string[];
  plan: string[];
  medication_instructions: string[];
  investigations: string[];
  follow_up: string | null;
  missing_information: string[];
  evidence_quotes?: Record<string, string>;
}

export interface ClinicalExtraction {
  id: string;
  consultation_id: string;
  extracted_data: ClinicalExtractionData;
  missing_information: string[];
  model_name?: string | null;
  is_mock: boolean;
  created_at: string;
  updated_at: string;
}

export type NoteStatus = "DRAFT" | "UNDER_REVIEW" | "APPROVED";

export interface ClinicalNote {
  id: string;
  consultation_id: string;
  version: number;
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
  status: NoteStatus;
  amendment_reason?: string | null;
  parent_note_id?: string | null;
  approved_by?: string | null;
  approved_at?: string | null;
  is_mock: boolean;
  created_at: string;
  updated_at: string;
}

export interface ConsultationSummary {
  id: string;
  doctor_id: string;
  patient_id: string;
  patient_name: string;
  patient_code: string;
  doctor_name: string;
  started_at: string;
  ended_at?: string | null;
  status: string;
  consent_status: "PENDING" | "GRANTED";
  transcription_status?: string | null;
  note_status?: string | null;
  audio_duration_seconds?: number | null;
  created_at: string;
}

export interface ConsultationDetail {
  id: string;
  doctor_id: string;
  patient_id: string;
  started_at: string;
  ended_at?: string | null;
  status: string;
  consent_status: "PENDING" | "GRANTED";
  consent_confirmed_at?: string | null;
  audio_filename?: string | null;
  audio_duration_seconds?: number | null;
  created_at: string;
  updated_at: string;
  patient: Patient;
  doctor_name: string;
  transcript?: Transcript | null;
  extraction?: ClinicalExtraction | null;
  latest_note?: ClinicalNote | null;
  note_versions: ClinicalNote[];
}

export interface DashboardData {
  stats: {
    total_patients: number;
    total_consultations: number;
    consultations_this_month: number;
    notes_awaiting_approval: number;
  };
  activity_last_7_days: Array<{
    date: string;
    label: string;
    consultations: number;
    approved_notes: number;
  }>;
  recent_consultations: Array<{
    id: string;
    patient_id: string;
    patient_name: string;
    patient_code: string;
    consultation_date: string;
    consultation_status: string;
    note_status: string;
  }>;
}

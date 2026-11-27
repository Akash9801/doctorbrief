import type {
  ClinicalExtraction,
  ClinicalNote,
  ConsultationDetail,
  ConsultationSummary,
  DashboardData,
  Doctor,
  Patient,
  TokenResponse,
  Transcript,
} from "@/types/api";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
const TOKEN_STORAGE_KEY = "doctorbrief_access_token";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredToken(token: string | null): void {
  if (token) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

let onUnauthorizedHandler: (() => void) | null = null;
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorizedHandler = handler;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getStoredToken();
  const headers = new Headers(options.headers || {});

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
    });
  } catch {
    throw new ApiError(
      "Unable to reach the server. Please check your internet connection and retry.",
      0
    );
  }

  if (response.status === 401) {
    if (onUnauthorizedHandler && !path.startsWith("/api/auth/login") && !path.startsWith("/api/auth/register")) {
      onUnauthorizedHandler();
    }
  }

  if (response.status === 204) {
    return undefined as T;
  }

  let data: any = null;
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    data = await response.json().catch(() => null);
  }

  if (!response.ok) {
    const detail =
      (data && typeof data.detail === "string" && data.detail) ||
      `Request failed with status ${response.status}`;
    throw new ApiError(detail, response.status);
  }

  return data as T;
}

export const authApi = {
  register: (payload: {
    full_name: string;
    email: string;
    password: string;
    specialty?: string;
    clinic_name?: string;
    phone?: string;
    registration_number?: string;
  }) =>
    request<TokenResponse>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  login: (payload: { email: string; password: string }) =>
    request<TokenResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  me: () => request<Doctor>("/api/auth/me"),

  updateProfile: (payload: {
    full_name?: string;
    specialty?: string;
    clinic_name?: string;
    phone?: string;
    registration_number?: string;
  }) =>
    request<Doctor>("/api/auth/me", {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
};

export const dashboardApi = {
  get: () => request<DashboardData>("/api/dashboard"),
};

export const patientsApi = {
  list: (params?: { search?: string; gender?: string }) => {
    const qs = new URLSearchParams();
    if (params?.search) qs.set("search", params.search);
    if (params?.gender && params.gender !== "all") qs.set("gender", params.gender);
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request<Patient[]>(`/api/patients${suffix}`);
  },

  get: (id: string) => request<Patient>(`/api/patients/${id}`),

  create: (payload: {
    full_name: string;
    date_of_birth?: string | null;
    age?: number | null;
    gender: string;
    phone: string;
    medical_history?: string;
    allergies?: string;
  }) =>
    request<Patient>("/api/patients", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  update: (
    id: string,
    payload: Partial<{
      full_name: string;
      date_of_birth: string | null;
      age: number | null;
      gender: string;
      phone: string;
      medical_history: string;
      allergies: string;
    }>
  ) =>
    request<Patient>(`/api/patients/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  delete: (id: string) =>
    request<void>(`/api/patients/${id}`, {
      method: "DELETE",
    }),

  history: (id: string) => request<ConsultationDetail[]>(`/api/patients/${id}/history`),
};

export const consultationsApi = {
  list: (params?: {
    search?: string;
    patient_id?: string;
    status?: string;
    date_from?: string;
    date_to?: string;
  }) => {
    const qs = new URLSearchParams();
    if (params?.search) qs.set("search", params.search);
    if (params?.patient_id) qs.set("patient_id", params.patient_id);
    if (params?.status && params.status !== "all") qs.set("status", params.status);
    if (params?.date_from) qs.set("date_from", params.date_from);
    if (params?.date_to) qs.set("date_to", params.date_to);
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request<ConsultationSummary[]>(`/api/consultations${suffix}`);
  },

  create: (payload: { patient_id: string; consent_status?: "PENDING" | "GRANTED" }) =>
    request<ConsultationDetail>("/api/consultations", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  get: (id: string) => request<ConsultationDetail>(`/api/consultations/${id}`),

  update: (
    id: string,
    payload: Partial<{
      status: string;
      consent_status: "PENDING" | "GRANTED";
      audio_duration_seconds: number;
    }>
  ) =>
    request<ConsultationDetail>(`/api/consultations/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  transcribe: (id: string, audioBlob: Blob, filename: string, durationSeconds?: number) => {
    const formData = new FormData();
    formData.append("file", audioBlob, filename);
    if (typeof durationSeconds === "number") {
      formData.append("duration_seconds", String(Math.round(durationSeconds)));
    }
    return request<Transcript>(`/api/consultations/${id}/transcribe`, {
      method: "POST",
      body: formData,
    });
  },

  updateTranscript: (id: string, payload: { edited_text: string; language?: string }) =>
    request<Transcript>(`/api/consultations/${id}/transcript`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  extract: (id: string) =>
    request<ClinicalExtraction>(`/api/consultations/${id}/extract`, {
      method: "POST",
    }),

  generateNote: (id: string) =>
    request<ClinicalNote>(`/api/consultations/${id}/generate-note`, {
      method: "POST",
    }),

  getNote: (id: string) => request<ClinicalNote>(`/api/consultations/${id}/note`),
};

export const notesApi = {
  update: (
    noteId: string,
    payload: Partial<{
      subjective: string;
      objective: string;
      assessment: string;
      plan: string;
      status: "DRAFT" | "UNDER_REVIEW";
    }>
  ) =>
    request<ClinicalNote>(`/api/notes/${noteId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  approve: (noteId: string, confirmAccuracy = true) =>
    request<ClinicalNote>(`/api/notes/${noteId}/approve`, {
      method: "POST",
      body: JSON.stringify({ confirm_accuracy: confirmAccuracy }),
    }),

  amend: (
    noteId: string,
    payload: {
      subjective: string;
      objective: string;
      assessment: string;
      plan: string;
      amendment_reason: string;
    }
  ) =>
    request<ClinicalNote>(`/api/notes/${noteId}/amend`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

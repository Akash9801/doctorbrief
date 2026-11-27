import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/contexts/AuthContext";
import { LoginPage } from "@/pages/LoginPage";
import { AddPatientPage } from "@/pages/AddPatientPage";
import { AudioRecorder } from "@/components/consultation/AudioRecorder";
import { TranscriptViewer } from "@/components/consultation/TranscriptViewer";
import { SoapEditor } from "@/components/consultation/SoapEditor";
import { ApprovalDialog } from "@/components/consultation/ApprovalDialog";
import type { ClinicalNote, Transcript } from "@/types/api";

function renderWithProviders(ui: React.ReactElement, initialEntries = ["/"]) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter initialEntries={initialEntries}>{ui}</MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

describe("DoctorBrief Frontend Core Workflows", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("handles doctor authentication login flow", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/api/auth/login")) {
        return new Response(
          JSON.stringify({
            access_token: "jwt-token-123",
            token_type: "bearer",
            doctor: {
              id: "doc-1",
              full_name: "Dr. Ananya Sharma",
              email: "dr.sharma@clinic.in",
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      }
      return new Response(JSON.stringify({ detail: "Not found" }), { status: 404 });
    });

    renderWithProviders(
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<div>Dashboard Home</div>} />
      </Routes>,
      ["/login"]
    );

    await user.type(screen.getByLabelText(/email address/i), "dr.sharma@clinic.in");
    await user.type(screen.getByLabelText(/password/i), "StrongPassword123!");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText("Dashboard Home")).toBeInTheDocument();
    });
    expect(localStorage.getItem("doctorbrief_access_token")).toBe("jwt-token-123");
    expect(fetchMock).toHaveBeenCalled();
  });

  it("validates and submits patient creation form", async () => {
    const user = userEvent.setup();
    localStorage.setItem("doctorbrief_access_token", "token-123");

    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/api/auth/me")) {
        return new Response(
          JSON.stringify({
            id: "doc-1",
            full_name: "Dr. Ananya Sharma",
            email: "dr.sharma@clinic.in",
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      }
      if (url.endsWith("/api/patients")) {
        return new Response(
          JSON.stringify({
            id: "pat-1",
            doctor_id: "doc-1",
            patient_code: "DB-0001",
            full_name: "Meera Nair",
            age: 42,
            gender: "Female",
            phone: "+91 9811122233",
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            consultation_count: 0,
          }),
          { status: 201, headers: { "Content-Type": "application/json" } }
        );
      }
      return new Response("{}", { status: 404 });
    });

    renderWithProviders(
      <Routes>
        <Route path="/patients/new" element={<AddPatientPage />} />
        <Route path="/patients/:id" element={<div>Patient Profile Created</div>} />
      </Routes>,
      ["/patients/new"]
    );

    await user.type(screen.getByLabelText(/full name/i), "Meera Nair");
    await user.type(screen.getByLabelText(/age/i), "42");
    await user.type(screen.getByLabelText(/phone number/i), "+91 9811122233");
    await user.click(screen.getByRole("button", { name: /create patient/i }));

    await waitFor(() => {
      expect(screen.getByText("Patient Profile Created")).toBeInTheDocument();
    });
  });

  it("enforces consent gate and transitions audio recorder states", async () => {
    const user = userEvent.setup();
    const onConfirmConsent = vi.fn().mockResolvedValue(undefined);
    const onUploadAudio = vi.fn().mockResolvedValue(undefined);

    const { rerender } = render(
      <AudioRecorder
        consentGranted={false}
        onConfirmConsent={onConfirmConsent}
        onUploadAudio={onUploadAudio}
        isUploading={false}
      />
    );

    const confirmBtn = screen.getByRole("button", {
      name: /confirm consent & enable microphone/i,
    });
    expect(confirmBtn).toBeDisabled();

    await user.click(screen.getByRole("checkbox"));
    expect(confirmBtn).toBeEnabled();
    await user.click(confirmBtn);
    expect(onConfirmConsent).toHaveBeenCalledTimes(1);

    // Mock MediaDevices & MediaRecorder for granted state
    const stopTrack = vi.fn();
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia: vi.fn().mockResolvedValue({
          getTracks: () => [{ stop: stopTrack }],
        }),
      },
    });
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:mock-audio"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });

    class MockMediaRecorder {
      static isTypeSupported = () => true;
      state: "inactive" | "recording" | "paused" = "inactive";
      mimeType = "audio/webm";
      ondataavailable: ((e: { data: Blob }) => void) | null = null;
      onstop: (() => void) | null = null;
      onerror: (() => void) | null = null;
      start() {
        this.state = "recording";
      }
      pause() {
        this.state = "paused";
      }
      resume() {
        this.state = "recording";
      }
      stop() {
        this.state = "inactive";
        this.ondataavailable?.({ data: new Blob(["audio-bytes"], { type: "audio/webm" }) });
        this.onstop?.();
      }
    }
    vi.stubGlobal("MediaRecorder", MockMediaRecorder);

    rerender(
      <AudioRecorder
        consentGranted={true}
        onConfirmConsent={onConfirmConsent}
        onUploadAudio={onUploadAudio}
        isUploading={false}
      />
    );

    await user.click(screen.getByRole("button", { name: /start recording/i }));
    expect(await screen.findByText(/recording in progress/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /pause/i }));
    expect(screen.getByText(/recording paused/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /resume/i }));
    expect(screen.getByText(/recording in progress/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /stop recording/i }));
    expect(await screen.findByText(/recording ready for transcription/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /upload & transcribe/i }));
    expect(onUploadAudio).toHaveBeenCalledTimes(1);
  });

  it("allows editing transcript and editing/approving SOAP note", async () => {
    const user = userEvent.setup();
    const onSaveTranscript = vi.fn().mockResolvedValue(undefined);
    const transcript: Transcript = {
      id: "t-1",
      consultation_id: "c-1",
      original_text: "Patient reports mild fever for 2 days.",
      edited_text: "Patient reports mild fever for 2 days.",
      language: "en",
      processing_status: "COMPLETED",
      is_mock: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    render(<TranscriptViewer transcript={transcript} onSaveTranscript={onSaveTranscript} />);
    const textarea = screen.getByLabelText(/editable consultation transcript/i);
    await user.type(textarea, " Temp 100 F.");
    await user.click(screen.getByRole("button", { name: /save transcript edits/i }));
    expect(onSaveTranscript).toHaveBeenCalledWith(
      "Patient reports mild fever for 2 days. Temp 100 F."
    );

    const onSaveDraft = vi.fn().mockResolvedValue(undefined);
    const onRegenerate = vi.fn().mockResolvedValue(undefined);
    const onRequestApprove = vi.fn();
    const onConfirmApprove = vi.fn().mockResolvedValue(undefined);

    const note: ClinicalNote = {
      id: "n-1",
      consultation_id: "c-1",
      version: 1,
      subjective: "Mild fever for 2 days.",
      objective: "Temp 100 F.",
      assessment: "Viral fever.",
      plan: "Paracetamol 500mg SOS.",
      status: "DRAFT",
      is_mock: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    const { rerender } = render(
      <>
        <SoapEditor
          note={note}
          onSaveDraft={onSaveDraft}
          onRegenerate={onRegenerate}
          onRequestApprove={onRequestApprove}
          onOpenAmend={vi.fn()}
          isSaving={false}
          isRegenerating={false}
        />
        <ApprovalDialog
          open={false}
          onOpenChange={vi.fn()}
          patientName="Meera Nair"
          missingInfoCount={0}
          onConfirmApprove={onConfirmApprove}
          isApproving={false}
        />
      </>
    );

    const planBox = screen.getByLabelText(/p — plan/i);
    await user.clear(planBox);
    await user.type(planBox, "Paracetamol 500mg SOS. Review in 3 days.");
    await user.click(screen.getByRole("button", { name: /save draft/i }));
    expect(onSaveDraft).toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: /approve & save note/i }));
    expect(onRequestApprove).toHaveBeenCalledTimes(1);

    rerender(
      <>
        <SoapEditor
          note={note}
          onSaveDraft={onSaveDraft}
          onRegenerate={onRegenerate}
          onRequestApprove={onRequestApprove}
          onOpenAmend={vi.fn()}
          isSaving={false}
          isRegenerating={false}
        />
        <ApprovalDialog
          open={true}
          onOpenChange={vi.fn()}
          patientName="Meera Nair"
          missingInfoCount={0}
          onConfirmApprove={onConfirmApprove}
          isApproving={false}
        />
      </>
    );

    await user.click(screen.getByRole("button", { name: /confirm & approve note/i }));
    expect(onConfirmApprove).toHaveBeenCalledTimes(1);
  });
});

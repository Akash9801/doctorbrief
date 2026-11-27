import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { AppLayout } from "@/components/layout/AppLayout";
import { LoginPage } from "@/pages/LoginPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { PatientsPage } from "@/pages/PatientsPage";
import { AddPatientPage } from "@/pages/AddPatientPage";
import { PatientProfilePage } from "@/pages/PatientProfilePage";
import { NewConsultationPage } from "@/pages/NewConsultationPage";
import { ConsultationRecordingPage } from "@/pages/ConsultationRecordingPage";
import { TranscriptReviewPage } from "@/pages/TranscriptReviewPage";
import { SoapNoteEditorPage } from "@/pages/SoapNoteEditorPage";
import { ConsultationHistoryPage } from "@/pages/ConsultationHistoryPage";
import { DoctorProfilePage } from "@/pages/DoctorProfilePage";
import { SettingsPage } from "@/pages/SettingsPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/patients" element={<PatientsPage />} />
          <Route path="/patients/new" element={<AddPatientPage />} />
          <Route path="/patients/:id" element={<PatientProfilePage />} />
          <Route path="/consultations" element={<ConsultationHistoryPage />} />
          <Route path="/consultations/new" element={<NewConsultationPage />} />
          <Route path="/consultations/:id/record" element={<ConsultationRecordingPage />} />
          <Route path="/consultations/:id/transcript" element={<TranscriptReviewPage />} />
          <Route path="/consultations/:id/note" element={<SoapNoteEditorPage />} />
          <Route path="/profile" element={<DoctorProfilePage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

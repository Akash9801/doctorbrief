import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, FileText } from "lucide-react";
import { consultationsApi } from "@/services/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/common/StatusBadge";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { ConsultationStepper } from "@/components/consultation/ConsultationStepper";
import { AudioRecorder } from "@/components/consultation/AudioRecorder";
import { PatientDetailsCard } from "@/components/patients/PatientDetailsCard";

export function ConsultationRecordingPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [uploadError, setUploadError] = useState<string | null>(null);

  const consultationQuery = useQuery({
    queryKey: ["consultation", id],
    queryFn: () => consultationsApi.get(id!),
    enabled: Boolean(id),
  });

  const consentMutation = useMutation({
    mutationFn: () => consultationsApi.update(id!, { consent_status: "GRANTED" }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["consultation", id], updated);
    },
  });

  const uploadMutation = useMutation({
    mutationFn: ({
      blob,
      filename,
      durationSeconds,
    }: {
      blob: Blob;
      filename: string;
      durationSeconds: number;
    }) => consultationsApi.transcribe(id!, blob, filename, durationSeconds),
    onSuccess: async () => {
      setUploadError(null);
      await queryClient.invalidateQueries({ queryKey: ["consultation", id] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      navigate(`/consultations/${id}/transcript`);
    },
    onError: (err: Error) => {
      setUploadError(err.message || "Audio transcription failed. Please retry.");
    },
  });

  if (consultationQuery.isLoading) {
    return <LoadingState message="Loading consultation workspace..." />;
  }

  if (consultationQuery.isError || !consultationQuery.data) {
    return (
      <ErrorState
        message={(consultationQuery.error as Error)?.message || "Consultation not found."}
        onRetry={() => consultationQuery.refetch()}
      />
    );
  }

  const consultation = consultationQuery.data;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Button asChild variant="ghost" size="sm">
            <Link to="/consultations">
              <ArrowLeft className="h-4 w-4" />
              <span>History</span>
            </Link>
          </Button>
          <StatusBadge status={consultation.status} />
          <StatusBadge status={consultation.consent_status} />
        </div>

        {consultation.transcript && (
          <Button asChild variant="outline" size="sm">
            <Link to={`/consultations/${id}/transcript`}>
              <FileText className="h-4 w-4" />
              <span>View Existing Transcript</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        )}
      </div>

      <ConsultationStepper
        consultationId={consultation.id}
        currentStep="record"
        hasTranscript={Boolean(consultation.transcript)}
        hasNote={Boolean(consultation.latest_note)}
        isApproved={consultation.latest_note?.status === "APPROVED"}
      />

      <PatientDetailsCard patient={consultation.patient} />

      <Card>
        <CardHeader>
          <CardTitle>Voice Consultation Recording</CardTitle>
          <CardDescription>
            Record the consultation naturally. When you stop recording, audio is securely uploaded
            to the server for speech-to-text transcription.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <AudioRecorder
            consentGranted={consultation.consent_status === "GRANTED"}
            onConfirmConsent={async () => {
              await consentMutation.mutateAsync();
            }}
            consentUpdating={consentMutation.isPending}
            isUploading={uploadMutation.isPending}
            uploadError={uploadError}
            onUploadAudio={async (blob, filename, durationSeconds) => {
              await uploadMutation.mutateAsync({ blob, filename, durationSeconds });
            }}
          />
        </CardContent>
      </Card>
    </div>
  );
}

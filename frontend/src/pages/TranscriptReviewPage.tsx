import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Sparkles,
  FileCheck2,
  AlertTriangle,
  ArrowRight,
  Loader2,
  Mic,
} from "lucide-react";
import { consultationsApi } from "@/services/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { ConsultationStepper } from "@/components/consultation/ConsultationStepper";
import { TranscriptViewer } from "@/components/consultation/TranscriptViewer";

export function TranscriptReviewPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [aiError, setAiError] = useState<string | null>(null);

  const consultationQuery = useQuery({
    queryKey: ["consultation", id],
    queryFn: () => consultationsApi.get(id!),
    enabled: Boolean(id),
  });

  const saveTranscriptMutation = useMutation({
    mutationFn: (editedText: string) =>
      consultationsApi.updateTranscript(id!, { edited_text: editedText }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["consultation", id] });
    },
  });

  const extractMutation = useMutation({
    mutationFn: () => consultationsApi.extract(id!),
    onSuccess: async () => {
      setAiError(null);
      await queryClient.invalidateQueries({ queryKey: ["consultation", id] });
    },
    onError: (err: Error) => {
      setAiError(err.message || "Clinical information extraction failed.");
    },
  });

  const generateNoteMutation = useMutation({
    mutationFn: () => consultationsApi.generateNote(id!),
    onSuccess: async () => {
      setAiError(null);
      await queryClient.invalidateQueries({ queryKey: ["consultation", id] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      navigate(`/consultations/${id}/note`);
    },
    onError: (err: Error) => {
      setAiError(err.message || "SOAP note generation failed.");
    },
  });

  if (consultationQuery.isLoading) {
    return <LoadingState message="Loading transcript review..." />;
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
  const transcript = consultation.transcript;
  const extraction = consultation.extraction;
  const extracted = extraction?.extracted_data;

  if (!transcript) {
    return (
      <div className="space-y-6">
        <ConsultationStepper
          consultationId={consultation.id}
          currentStep="transcript"
          hasTranscript={false}
          hasNote={Boolean(consultation.latest_note)}
        />
        <Alert variant="warning" title="No Transcript Available Yet">
          Record and upload consultation audio first to generate a transcript.
        </Alert>
        <Button asChild>
          <Link to={`/consultations/${consultation.id}/record`}>
            <Mic className="h-4 w-4" />
            <span>Go to Recording</span>
          </Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <ConsultationStepper
        consultationId={consultation.id}
        currentStep="transcript"
        hasTranscript={true}
        hasNote={Boolean(consultation.latest_note)}
        isApproved={consultation.latest_note?.status === "APPROVED"}
      />

      {aiError && (
        <Alert variant="destructive" title="AI Processing Error">
          {aiError}
        </Alert>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4">
        <div>
          <p className="text-sm font-semibold text-slate-900">
            Patient: {consultation.patient.full_name} ({consultation.patient.patient_code})
          </p>
          <p className="text-xs text-slate-500">
            Review or correct the transcript, extract structured clinical facts, and draft a SOAP note.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <Button
            type="button"
            variant="outline"
            onClick={() => extractMutation.mutate()}
            disabled={extractMutation.isPending || generateNoteMutation.isPending}
          >
            {extractMutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Extracting Clinical Info...</span>
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                <span>{extraction ? "Re-extract Clinical Info" : "Extract Clinical Info"}</span>
              </>
            )}
          </Button>

          <Button
            type="button"
            onClick={() => generateNoteMutation.mutate()}
            disabled={generateNoteMutation.isPending || extractMutation.isPending}
          >
            {generateNoteMutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Generating SOAP Draft...</span>
              </>
            ) : (
              <>
                <FileCheck2 className="h-4 w-4" />
                <span>Generate SOAP Note</span>
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <TranscriptViewer
          transcript={transcript}
          onSaveTranscript={async (editedText) => {
            await saveTranscriptMutation.mutateAsync(editedText);
          }}
          isSaving={saveTranscriptMutation.isPending}
        />

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Extracted Clinical Information</CardTitle>
                <CardDescription>
                  Strictly grounded in transcript facts — missing fields are flagged below
                </CardDescription>
              </div>
              {extraction?.is_mock && <Badge variant="warning">Dev Mock</Badge>}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {!extracted ? (
              <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center">
                <p className="text-sm text-slate-600">
                  Click <strong>Extract Clinical Info</strong> or{" "}
                  <strong>Generate SOAP Note</strong> to analyze this transcript.
                </p>
              </div>
            ) : (
              <div className="space-y-4 text-sm">
                {extraction.missing_information.length > 0 && (
                  <Alert variant="warning" title="Missing / Undocumented Information">
                    <ul className="mt-1 list-disc space-y-0.5 pl-4">
                      {extraction.missing_information.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </Alert>
                )}

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <InfoBlock
                    label="Chief Complaint"
                    value={extracted.chief_complaint || "Not documented"}
                  />
                  <InfoBlock
                    label="Symptom Duration"
                    value={extracted.symptom_duration || "Not stated"}
                  />
                </div>

                <ListBlock label="Patient-Reported Symptoms" items={extracted.symptoms} />
                <ListBlock label="Medical History" items={extracted.medical_history} />
                <ListBlock label="Allergies" items={extracted.allergies} />

                {Object.keys(extracted.vitals || {}).length > 0 && (
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                      Vitals Mentioned
                    </p>
                    <div className="mt-1.5 flex flex-wrap gap-2">
                      {Object.entries(extracted.vitals).map(([k, v]) => (
                        <Badge key={k} variant="secondary">
                          {k}: {v}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                <ListBlock
                  label="Examination Findings (Doctor Stated)"
                  items={extracted.examination_findings}
                />
                <ListBlock label="Assessment (Doctor Stated)" items={extracted.assessment} />
                <ListBlock
                  label="Medication Instructions"
                  items={extracted.medication_instructions}
                />
                <ListBlock label="Treatment Plan & Investigations" items={[...extracted.plan, ...extracted.investigations]} />

                {extracted.follow_up && (
                  <InfoBlock label="Follow-up Instructions" value={extracted.follow_up} />
                )}

                {extraction.missing_information.length === 0 && (
                  <div className="flex items-center gap-2 text-xs text-emerald-700">
                    <AlertTriangle className="h-3.5 w-3.5" />
                    <span>All primary clinical sections were documented in the transcript.</span>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function InfoBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</p>
      <p className="mt-1 text-slate-900">{value}</p>
    </div>
  );
}

function ListBlock({ label, items }: { label: string; items: string[] }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</p>
      <ul className="mt-1 list-disc space-y-0.5 pl-4 text-slate-900">
        {items.map((item, idx) => (
          <li key={idx}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileCheck2, Loader2, History } from "lucide-react";
import { consultationsApi, notesApi } from "@/services/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert } from "@/components/ui/alert";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { StatusBadge } from "@/components/common/StatusBadge";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { ConsultationStepper } from "@/components/consultation/ConsultationStepper";
import { SoapEditor } from "@/components/consultation/SoapEditor";
import { ApprovalDialog } from "@/components/consultation/ApprovalDialog";
import { formatDateTime } from "@/lib/utils";

export function SoapNoteEditorPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [approveOpen, setApproveOpen] = useState(false);
  const [amendOpen, setAmendOpen] = useState(false);
  const [amendReason, setAmendReason] = useState("");
  const [amendFields, setAmendFields] = useState({
    subjective: "",
    objective: "",
    assessment: "",
    plan: "",
  });
  const [actionError, setActionError] = useState<string | null>(null);

  const consultationQuery = useQuery({
    queryKey: ["consultation", id],
    queryFn: () => consultationsApi.get(id!),
    enabled: Boolean(id),
  });

  const refreshConsultation = async () => {
    await queryClient.invalidateQueries({ queryKey: ["consultation", id] });
    await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    await queryClient.invalidateQueries({ queryKey: ["consultations"] });
  };

  const generateMutation = useMutation({
    mutationFn: () => consultationsApi.generateNote(id!),
    onSuccess: async () => {
      setActionError(null);
      await refreshConsultation();
    },
    onError: (err: Error) => {
      setActionError(err.message || "Failed to generate SOAP note.");
    },
  });

  const saveMutation = useMutation({
    mutationFn: ({
      noteId,
      payload,
    }: {
      noteId: string;
      payload: {
        subjective: string;
        objective: string;
        assessment: string;
        plan: string;
        status?: "DRAFT" | "UNDER_REVIEW";
      };
    }) => notesApi.update(noteId, payload),
    onSuccess: async () => {
      setActionError(null);
      await refreshConsultation();
    },
    onError: (err: Error) => {
      setActionError(err.message || "Failed to save note draft.");
    },
  });

  const approveMutation = useMutation({
    mutationFn: (noteId: string) => notesApi.approve(noteId, true),
    onSuccess: async () => {
      setActionError(null);
      setApproveOpen(false);
      await refreshConsultation();
    },
    onError: (err: Error) => {
      setActionError(err.message || "Approval failed.");
    },
  });

  const amendMutation = useMutation({
    mutationFn: (noteId: string) =>
      notesApi.amend(noteId, {
        ...amendFields,
        amendment_reason: amendReason,
      }),
    onSuccess: async () => {
      setActionError(null);
      setAmendOpen(false);
      setAmendReason("");
      await refreshConsultation();
    },
    onError: (err: Error) => {
      setActionError(err.message || "Failed to create amendment.");
    },
  });

  if (consultationQuery.isLoading) {
    return <LoadingState message="Loading SOAP note workspace..." />;
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
  const note = consultation.latest_note;
  const transcriptText =
    consultation.transcript?.edited_text || consultation.transcript?.original_text || "";
  const missingInfo = consultation.extraction?.missing_information || [];

  const openAmendModal = () => {
    if (!note) return;
    setAmendFields({
      subjective: note.subjective,
      objective: note.objective,
      assessment: note.assessment,
      plan: note.plan,
    });
    setAmendReason("");
    setAmendOpen(true);
  };

  return (
    <div className="space-y-6">
      <ConsultationStepper
        consultationId={consultation.id}
        currentStep="note"
        hasTranscript={Boolean(consultation.transcript)}
        hasNote={Boolean(note)}
        isApproved={note?.status === "APPROVED"}
      />

      {actionError && (
        <Alert variant="destructive" title="Clinical Note Action Failed">
          {actionError}
        </Alert>
      )}

      {!note ? (
        <Card>
          <CardHeader>
            <CardTitle>No SOAP Note Generated Yet</CardTitle>
            <CardDescription>
              Generate a structured SOAP note draft from the consultation transcript.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              type="button"
              onClick={() => generateMutation.mutate()}
              disabled={!consultation.transcript || generateMutation.isPending}
            >
              {generateMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Generating SOAP Draft...</span>
                </>
              ) : (
                <>
                  <FileCheck2 className="h-4 w-4" />
                  <span>Generate SOAP Note Draft</span>
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
          <div className="xl:col-span-2 space-y-5">
            {missingInfo.length > 0 && note.status !== "APPROVED" && (
              <Alert variant="warning" title="Missing Information Warnings">
                <ul className="mt-1 list-disc space-y-0.5 pl-4">
                  {missingInfo.map((m, idx) => (
                    <li key={idx}>{m}</li>
                  ))}
                </ul>
              </Alert>
            )}

            <SoapEditor
              note={note}
              isSaving={saveMutation.isPending}
              isRegenerating={generateMutation.isPending}
              onSaveDraft={async (payload) => {
                await saveMutation.mutateAsync({ noteId: note.id, payload });
              }}
              onRegenerate={async () => {
                await generateMutation.mutateAsync();
              }}
              onRequestApprove={() => setApproveOpen(true)}
              onOpenAmend={openAmendModal}
            />

            {consultation.note_versions.length > 1 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-sm">
                    <History className="h-4 w-4 text-slate-500" />
                    <span>Note Version History</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2.5">
                  {consultation.note_versions.map((v) => (
                    <div
                      key={v.id}
                      className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-xs"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-slate-900">Version {v.version}</span>
                        <StatusBadge status={v.status} />
                        {v.amendment_reason && (
                          <span className="text-slate-600">— {v.amendment_reason}</span>
                        )}
                      </div>
                      <span className="text-slate-500">{formatDateTime(v.updated_at)}</span>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}
          </div>

          <div className="space-y-5">
            <Card>
              <CardHeader>
                <CardTitle>Transcript Reference</CardTitle>
                <CardDescription>
                  Compare the SOAP note against the original consultation transcript
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="max-h-96 overflow-y-auto whitespace-pre-wrap rounded-lg border border-slate-200 bg-slate-50 p-3.5 text-sm leading-relaxed text-slate-800">
                  {transcriptText || "No transcript available."}
                </div>
                <Button asChild variant="outline" size="sm" className="w-full">
                  <Link to={`/consultations/${consultation.id}/transcript`}>
                    Open Full Transcript & Extraction
                  </Link>
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {note && (
        <ApprovalDialog
          open={approveOpen}
          onOpenChange={setApproveOpen}
          patientName={consultation.patient.full_name}
          missingInfoCount={missingInfo.length}
          isApproving={approveMutation.isPending}
          onConfirmApprove={async () => {
            await approveMutation.mutateAsync(note.id);
          }}
        />
      )}

      <Dialog open={amendOpen} onOpenChange={setAmendOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Create Versioned Amendment</DialogTitle>
            <DialogDescription>
              Approved clinical notes are immutable. Submitting creates a new draft version while
              preserving the earlier approved record.
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-[60vh] space-y-3 overflow-y-auto pr-1">
            <div className="space-y-1">
              <Label>Reason for Amendment</Label>
              <Textarea
                rows={2}
                placeholder="e.g., Added patient-reported blood pressure log and follow-up lab advice"
                value={amendReason}
                onChange={(e) => setAmendReason(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label>Subjective</Label>
              <Textarea
                rows={3}
                value={amendFields.subjective}
                onChange={(e) =>
                  setAmendFields((f) => ({ ...f, subjective: e.target.value }))
                }
              />
            </div>
            <div className="space-y-1">
              <Label>Objective</Label>
              <Textarea
                rows={3}
                value={amendFields.objective}
                onChange={(e) =>
                  setAmendFields((f) => ({ ...f, objective: e.target.value }))
                }
              />
            </div>
            <div className="space-y-1">
              <Label>Assessment</Label>
              <Textarea
                rows={2}
                value={amendFields.assessment}
                onChange={(e) =>
                  setAmendFields((f) => ({ ...f, assessment: e.target.value }))
                }
              />
            </div>
            <div className="space-y-1">
              <Label>Plan</Label>
              <Textarea
                rows={3}
                value={amendFields.plan}
                onChange={(e) => setAmendFields((f) => ({ ...f, plan: e.target.value }))}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAmendOpen(false)}>
              Cancel
            </Button>
            <Button
              disabled={amendReason.trim().length < 3 || amendMutation.isPending || !note}
              onClick={() => note && amendMutation.mutate(note.id)}
            >
              {amendMutation.isPending ? "Creating Amendment..." : "Create Draft Amendment"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

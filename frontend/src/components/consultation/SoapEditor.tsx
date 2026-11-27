import { useEffect, useState } from "react";
import { Save, Sparkles, CheckCircle2, Lock, FilePenLine, Loader2, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Alert } from "@/components/ui/alert";
import { StatusBadge } from "@/components/common/StatusBadge";
import type { ClinicalNote } from "@/types/api";
import { formatDateTime } from "@/lib/utils";

interface SoapEditorProps {
  note: ClinicalNote;
  onSaveDraft: (payload: {
    subjective: string;
    objective: string;
    assessment: string;
    plan: string;
    status?: "DRAFT" | "UNDER_REVIEW";
  }) => Promise<void>;
  onRegenerate: () => Promise<void>;
  onRequestApprove: () => void;
  onOpenAmend: () => void;
  isSaving: boolean;
  isRegenerating: boolean;
}

export function SoapEditor({
  note,
  onSaveDraft,
  onRegenerate,
  onRequestApprove,
  onOpenAmend,
  isSaving,
  isRegenerating,
}: SoapEditorProps) {
  const [subjective, setSubjective] = useState(note.subjective);
  const [objective, setObjective] = useState(note.objective);
  const [assessment, setAssessment] = useState(note.assessment);
  const [plan, setPlan] = useState(note.plan);
  const [savedNotice, setSavedNotice] = useState(false);

  useEffect(() => {
    setSubjective(note.subjective);
    setObjective(note.objective);
    setAssessment(note.assessment);
    setPlan(note.plan);
  }, [note.id, note.subjective, note.objective, note.assessment, note.plan]);

  const isApproved = note.status === "APPROVED";
  const isDirty =
    subjective !== note.subjective ||
    objective !== note.objective ||
    assessment !== note.assessment ||
    plan !== note.plan;

  const handleSave = async (status?: "DRAFT" | "UNDER_REVIEW") => {
    await onSaveDraft({ subjective, objective, assessment, plan, status });
    setSavedNotice(true);
    window.setTimeout(() => setSavedNotice(false), 2500);
  };

  return (
    <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-5">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-base font-semibold text-slate-900">
              SOAP Clinical Note (v{note.version})
            </h3>
            <StatusBadge status={note.status} />
            {note.is_mock && <StatusBadge status="DEV_MOCK" />}
          </div>
          {note.approved_at && (
            <p className="text-xs text-emerald-700">
              Approved on {formatDateTime(note.approved_at)}
            </p>
          )}
          {note.amendment_reason && (
            <p className="text-xs text-slate-600">
              Amendment reason: {note.amendment_reason}
            </p>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {!isApproved ? (
            <>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={onRegenerate}
                disabled={isRegenerating || isSaving}
              >
                {isRegenerating ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    <span>Regenerating...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="h-3.5 w-3.5" />
                    <span>Regenerate Draft</span>
                  </>
                )}
              </Button>

              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => handleSave("UNDER_REVIEW")}
                disabled={isSaving || isRegenerating}
              >
                {isSaving ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    <span>Saving...</span>
                  </>
                ) : savedNotice ? (
                  <>
                    <Check className="h-3.5 w-3.5" />
                    <span>Saved</span>
                  </>
                ) : (
                  <>
                    <Save className="h-3.5 w-3.5" />
                    <span>{isDirty ? "Save Draft" : "Mark Under Review"}</span>
                  </>
                )}
              </Button>

              <Button
                type="button"
                variant="success"
                size="sm"
                onClick={onRequestApprove}
                disabled={isSaving || isRegenerating}
              >
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>Approve & Save Note</span>
              </Button>
            </>
          ) : (
            <Button type="button" variant="outline" size="sm" onClick={onOpenAmend}>
              <FilePenLine className="h-3.5 w-3.5" />
              <span>Create Amendment</span>
            </Button>
          )}
        </div>
      </div>

      {isApproved && (
        <Alert variant="success" title="Approved Clinical Record">
          <div className="flex items-center gap-1.5">
            <Lock className="h-3.5 w-3.5 shrink-0" />
            <span>
              This note version is locked and recorded in the patient&apos;s medical history. To
              make updates, create a versioned amendment.
            </span>
          </div>
        </Alert>
      )}

      <div className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="soap-subjective" className="text-xs font-semibold uppercase tracking-wider text-slate-600">
            S — Subjective
          </Label>
          <Textarea
            id="soap-subjective"
            value={subjective}
            onChange={(e) => setSubjective(e.target.value)}
            disabled={isApproved}
            rows={4}
            placeholder="Chief complaint, patient-reported symptoms, duration, relevant history..."
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="soap-objective" className="text-xs font-semibold uppercase tracking-wider text-slate-600">
            O — Objective
          </Label>
          <Textarea
            id="soap-objective"
            value={objective}
            onChange={(e) => setObjective(e.target.value)}
            disabled={isApproved}
            rows={4}
            placeholder="Explicitly documented vitals and physical examination findings..."
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="soap-assessment" className="text-xs font-semibold uppercase tracking-wider text-slate-600">
            A — Assessment
          </Label>
          <Textarea
            id="soap-assessment"
            value={assessment}
            onChange={(e) => setAssessment(e.target.value)}
            disabled={isApproved}
            rows={3}
            placeholder="Doctor-stated clinical assessment and differential diagnoses..."
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="soap-plan" className="text-xs font-semibold uppercase tracking-wider text-slate-600">
            P — Plan
          </Label>
          <Textarea
            id="soap-plan"
            value={plan}
            onChange={(e) => setPlan(e.target.value)}
            disabled={isApproved}
            rows={4}
            placeholder="Treatment plan, medication instructions, investigations, follow-up..."
          />
        </div>
      </div>
    </div>
  );
}

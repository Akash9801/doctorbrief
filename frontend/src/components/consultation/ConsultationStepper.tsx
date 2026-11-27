import { Link } from "react-router-dom";
import { Check, Mic, FileText, ClipboardCheck } from "lucide-react";
import { cn } from "@/lib/utils";

interface ConsultationStepperProps {
  consultationId: string;
  currentStep: "record" | "transcript" | "note";
  hasTranscript: boolean;
  hasNote: boolean;
  isApproved?: boolean;
}

export function ConsultationStepper({
  consultationId,
  currentStep,
  hasTranscript,
  hasNote,
  isApproved,
}: ConsultationStepperProps) {
  const steps = [
    {
      id: "record" as const,
      label: "1. Record Audio",
      to: `/consultations/${consultationId}/record`,
      icon: Mic,
      completed: hasTranscript,
      enabled: true,
    },
    {
      id: "transcript" as const,
      label: "2. Transcript & Extraction",
      to: `/consultations/${consultationId}/transcript`,
      icon: FileText,
      completed: hasNote,
      enabled: hasTranscript,
    },
    {
      id: "note" as const,
      label: "3. SOAP Note & Approval",
      to: `/consultations/${consultationId}/note`,
      icon: ClipboardCheck,
      completed: Boolean(isApproved),
      enabled: hasNote || hasTranscript,
    },
  ];

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3 sm:p-4">
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        {steps.map((step) => {
          const Icon = step.icon;
          const isCurrent = step.id === currentStep;
          const content = (
            <div
              className={cn(
                "flex items-center gap-3 rounded-lg border px-3.5 py-2.5 text-sm font-medium transition-colors",
                isCurrent
                  ? "border-primary bg-primary/5 text-primary"
                  : step.completed
                  ? "border-emerald-200 bg-emerald-50/70 text-emerald-800 hover:bg-emerald-50"
                  : step.enabled
                  ? "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                  : "cursor-not-allowed border-slate-100 bg-slate-50 text-slate-400"
              )}
            >
              <span
                className={cn(
                  "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs",
                  isCurrent
                    ? "bg-primary text-white"
                    : step.completed
                    ? "bg-emerald-600 text-white"
                    : "bg-slate-200 text-slate-600"
                )}
              >
                {step.completed && !isCurrent ? <Check className="h-3.5 w-3.5" /> : <Icon className="h-3.5 w-3.5" />}
              </span>
              <span className="truncate">{step.label}</span>
            </div>
          );

          return step.enabled ? (
            <Link key={step.id} to={step.to}>
              {content}
            </Link>
          ) : (
            <div key={step.id}>{content}</div>
          );
        })}
      </div>
    </div>
  );
}

import { ShieldCheck, Mic, FileWarning } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert } from "@/components/ui/alert";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";

export function SettingsPage() {
  const { doctor, logout } = useAuth();

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Settings & Clinical Safeguards</h2>
        <p className="text-sm text-slate-500">
          Review documentation workflow controls, consent policies, and session security.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-primary" />
            <span>Clinical Documentation Safeguards</span>
          </CardTitle>
          <CardDescription>
            Built-in safety controls enforced across every consultation
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-slate-700">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3.5">
            <p className="font-semibold text-slate-900">Explicit Patient Consent Gate</p>
            <p className="mt-1">
              Microphone access and audio transcription remain locked until patient consent is
              explicitly confirmed for each consultation.
            </p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3.5">
            <p className="font-semibold text-slate-900">Mandatory Doctor Approval</p>
            <p className="mt-1">
              All AI-generated SOAP notes are stored as drafts and require explicit clinician
              review and approval before entering patient history.
            </p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3.5">
            <p className="font-semibold text-slate-900">Immutable Approved Versions</p>
            <p className="mt-1">
              Approved notes cannot be silently overwritten. Subsequent edits create a new
              versioned amendment with a documented reason.
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mic className="h-5 w-5 text-primary" />
            <span>Audio & Transcription Mode</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-slate-700">
          <p>
            Audio is captured locally in the browser using WebM/Opus (or browser-supported format)
            and uploaded upon stopping recording to the backend transcription service powered by{" "}
            <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">gpt-transcribe</code>.
          </p>
          <Alert variant="default" title="Prototype Notice">
            <div className="flex items-start gap-2">
              <FileWarning className="mt-0.5 h-4 w-4 shrink-0 text-slate-600" />
              <span>
                DoctorBrief is a clinical documentation assistant prototype, not a diagnostic
                system, autonomous prescriber, or certified medical device.
              </span>
            </div>
          </Alert>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Active Session</CardTitle>
          <CardDescription>Signed in as {doctor?.email}</CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="outline" onClick={logout}>
            Sign Out of This Device
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

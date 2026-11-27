import { useEffect, useRef, useState } from "react";
import {
  Mic,
  Pause,
  Play,
  Square,
  RotateCcw,
  Upload,
  AlertCircle,
  Loader2,
  ShieldCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";
import { formatDuration } from "@/lib/utils";
import { AudioPlayer } from "@/components/consultation/AudioPlayer";

export type RecorderState =
  | "idle"
  | "recording"
  | "paused"
  | "stopped"
  | "uploading"
  | "error";

interface AudioRecorderProps {
  consentGranted: boolean;
  onConfirmConsent: () => Promise<void>;
  consentUpdating?: boolean;
  onUploadAudio: (blob: Blob, filename: string, durationSeconds: number) => Promise<void>;
  isUploading: boolean;
  uploadError?: string | null;
}

function getPreferredMimeType(): string {
  if (typeof MediaRecorder === "undefined") return "";
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/mp4",
  ];
  for (const type of candidates) {
    if (typeof MediaRecorder.isTypeSupported === "function" && MediaRecorder.isTypeSupported(type)) {
      return type;
    }
  }
  return "";
}

function extensionForMime(mimeType: string): string {
  if (mimeType.includes("ogg")) return "ogg";
  if (mimeType.includes("mp4")) return "m4a";
  if (mimeType.includes("wav")) return "wav";
  return "webm";
}

export function AudioRecorder({
  consentGranted,
  onConfirmConsent,
  consentUpdating,
  onUploadAudio,
  isUploading,
  uploadError,
}: AudioRecorderProps) {
  const [recorderState, setRecorderState] = useState<RecorderState>("idle");
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [mimeType, setMimeType] = useState<string>("audio/webm");
  const [consentChecked, setConsentChecked] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const timerRef = useRef<number | null>(null);

  const browserSupported =
    typeof window !== "undefined" &&
    typeof navigator !== "undefined" &&
    Boolean(navigator.mediaDevices?.getUserMedia) &&
    typeof MediaRecorder !== "undefined";

  useEffect(() => {
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
      if (audioUrl) URL.revokeObjectURL(audioUrl);
    };
  }, [audioUrl]);

  const stopTimer = () => {
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  const startTimer = () => {
    stopTimer();
    timerRef.current = window.setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);
  };

  const cleanupStream = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  };

  const handleStartRecording = async () => {
    setErrorMessage(null);

    if (!consentGranted) {
      setErrorMessage("Please confirm patient recording consent before accessing the microphone.");
      return;
    }
    if (!browserSupported) {
      setErrorMessage(
        "Your browser does not support in-browser audio recording (MediaRecorder API). Please use a modern version of Chrome, Edge, or Firefox."
      );
      setRecorderState("error");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];

      const preferred = getPreferredMimeType();
      const recorder = preferred
        ? new MediaRecorder(stream, { mimeType: preferred })
        : new MediaRecorder(stream);

      const resolvedMime = recorder.mimeType || preferred || "audio/webm";
      setMimeType(resolvedMime);

      recorder.ondataavailable = (event: BlobEvent) => {
        if (event.data && event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        stopTimer();
        cleanupStream();
        const blob = new Blob(chunksRef.current, { type: resolvedMime });
        if (blob.size === 0) {
          setErrorMessage("No audio data was captured. Please check your microphone and try again.");
          setRecorderState("error");
          return;
        }
        if (audioUrl) URL.revokeObjectURL(audioUrl);
        const url = URL.createObjectURL(blob);
        setAudioBlob(blob);
        setAudioUrl(url);
        setRecorderState("stopped");
      };

      recorder.onerror = () => {
        stopTimer();
        cleanupStream();
        setErrorMessage("An error occurred during audio recording. Please try again.");
        setRecorderState("error");
      };

      mediaRecorderRef.current = recorder;
      recorder.start(1000);
      setElapsedSeconds(0);
      setAudioBlob(null);
      setRecorderState("recording");
      startTimer();
    } catch (err: any) {
      cleanupStream();
      const name = err?.name || "";
      if (name === "NotAllowedError" || name === "PermissionDeniedError") {
        setErrorMessage(
          "Microphone permission was denied. Allow microphone access in your browser address bar and try again."
        );
      } else if (name === "NotFoundError" || name === "DevicesNotFoundError") {
        setErrorMessage("No microphone device was detected. Connect a microphone and try again.");
      } else {
        setErrorMessage("Unable to access microphone. Please verify device permissions and retry.");
      }
      setRecorderState("error");
    }
  };

  const handlePauseRecording = () => {
    const rec = mediaRecorderRef.current;
    if (rec && rec.state === "recording") {
      rec.pause();
      stopTimer();
      setRecorderState("paused");
    }
  };

  const handleResumeRecording = () => {
    const rec = mediaRecorderRef.current;
    if (rec && rec.state === "paused") {
      rec.resume();
      startTimer();
      setRecorderState("recording");
    }
  };

  const handleStopRecording = () => {
    const rec = mediaRecorderRef.current;
    if (rec && (rec.state === "recording" || rec.state === "paused")) {
      rec.stop();
    }
  };

  const handleReset = () => {
    stopTimer();
    cleanupStream();
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudioBlob(null);
    setAudioUrl(null);
    setElapsedSeconds(0);
    setErrorMessage(null);
    setRecorderState("idle");
  };

  const handleUpload = async () => {
    if (!audioBlob) return;
    setErrorMessage(null);
    const ext = extensionForMime(mimeType);
    const filename = `consultation-${Date.now()}.${ext}`;
    await onUploadAudio(audioBlob, filename, elapsedSeconds);
  };

  if (!consentGranted) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-6">
        <div className="flex items-start gap-3">
          <ShieldCheck className="mt-0.5 h-6 w-6 shrink-0 text-amber-700" />
          <div className="space-y-3">
            <div>
              <h3 className="text-base font-semibold text-slate-900">
                Patient Consent Required Before Recording
              </h3>
              <p className="mt-1 text-sm text-slate-700">
                Before enabling the microphone, inform the patient that this consultation will be
                recorded and processed by AI solely to assist with clinical documentation.
              </p>
            </div>
            <label className="flex cursor-pointer items-start gap-2.5 rounded-lg border border-amber-200 bg-white p-3 text-sm text-slate-800">
              <input
                type="checkbox"
                checked={consentChecked}
                onChange={(e) => setConsentChecked(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-slate-300 text-primary focus:ring-primary"
              />
              <span>
                I confirm that the patient has been informed and has provided explicit verbal or
                written consent to record this consultation.
              </span>
            </label>
            <Button
              type="button"
              disabled={!consentChecked || consentUpdating}
              onClick={onConfirmConsent}
            >
              {consentUpdating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Confirming Consent...</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="h-4 w-4" />
                  <span>Confirm Consent & Enable Microphone</span>
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5 rounded-xl border border-slate-200 bg-white p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span
              className={`h-2.5 w-2.5 rounded-full ${
                recorderState === "recording"
                  ? "animate-pulse bg-red-600"
                  : recorderState === "paused"
                  ? "bg-amber-500"
                  : recorderState === "stopped"
                  ? "bg-emerald-600"
                  : "bg-slate-300"
              }`}
            />
            <span className="text-sm font-semibold text-slate-900">
              {recorderState === "recording"
                ? "Recording in progress"
                : recorderState === "paused"
                ? "Recording paused"
                : recorderState === "stopped"
                ? "Recording ready for transcription"
                : "Microphone ready"}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Completed audio is uploaded securely for transcription after you stop recording.
          </p>
        </div>

        <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-2 text-right">
          <span className="block text-[11px] font-medium uppercase tracking-wider text-slate-500">
            Duration
          </span>
          <span
            data-testid="recording-timer"
            className="tabular-nums text-2xl font-bold text-slate-900"
          >
            {formatDuration(elapsedSeconds)}
          </span>
        </div>
      </div>

      {!browserSupported && (
        <Alert variant="destructive" title="Unsupported Browser">
          Your browser does not support the MediaRecorder API. Please use Chrome, Edge, or Firefox.
        </Alert>
      )}

      {(errorMessage || uploadError) && (
        <Alert variant="destructive" title="Recording / Upload Issue">
          {uploadError || errorMessage}
        </Alert>
      )}

      <div className="flex flex-wrap items-center gap-3">
        {(recorderState === "idle" || recorderState === "error") && (
          <Button
            type="button"
            size="lg"
            onClick={handleStartRecording}
            disabled={!browserSupported || isUploading}
          >
            <Mic className="h-4 w-4" />
            <span>Start Recording</span>
          </Button>
        )}

        {recorderState === "recording" && (
          <>
            <Button type="button" variant="outline" size="lg" onClick={handlePauseRecording}>
              <Pause className="h-4 w-4" />
              <span>Pause</span>
            </Button>
            <Button type="button" variant="destructive" size="lg" onClick={handleStopRecording}>
              <Square className="h-4 w-4" />
              <span>Stop Recording</span>
            </Button>
          </>
        )}

        {recorderState === "paused" && (
          <>
            <Button type="button" size="lg" onClick={handleResumeRecording}>
              <Play className="h-4 w-4" />
              <span>Resume</span>
            </Button>
            <Button type="button" variant="destructive" size="lg" onClick={handleStopRecording}>
              <Square className="h-4 w-4" />
              <span>Stop Recording</span>
            </Button>
          </>
        )}

        {recorderState === "stopped" && audioBlob && (
          <>
            <Button type="button" size="lg" onClick={handleUpload} disabled={isUploading}>
              {isUploading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Uploading & Transcribing...</span>
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4" />
                  <span>{uploadError ? "Retry Transcription" : "Upload & Transcribe"}</span>
                </>
              )}
            </Button>
            <Button type="button" variant="outline" size="lg" onClick={handleReset} disabled={isUploading}>
              <RotateCcw className="h-4 w-4" />
              <span>Record Again</span>
            </Button>
          </>
        )}
      </div>

      {isUploading && (
        <div className="space-y-2 rounded-lg border border-sky-200 bg-sky-50 p-3.5 text-sm text-sky-900">
          <div className="flex items-center gap-2 font-medium">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>Uploading audio and generating transcript with OpenAI...</span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-sky-200">
            <div className="h-full w-2/3 animate-pulse rounded-full bg-primary" />
          </div>
        </div>
      )}

      {recorderState === "stopped" && audioUrl && (
        <div className="pt-2">
          <AudioPlayer src={audioUrl} durationSeconds={elapsedSeconds} />
        </div>
      )}

      {!errorMessage && browserSupported && recorderState === "idle" && (
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <AlertCircle className="h-3.5 w-3.5" />
          <span>Speak naturally with your patient. You can pause or resume at any time.</span>
        </div>
      )}
    </div>
  );
}

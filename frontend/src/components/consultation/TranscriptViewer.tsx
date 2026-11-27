import { useEffect, useState } from "react";
import { Save, RotateCcw, Loader2, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import type { Transcript } from "@/types/api";

interface TranscriptViewerProps {
  transcript: Transcript;
  onSaveTranscript: (editedText: string) => Promise<void>;
  isSaving?: boolean;
}

export function TranscriptViewer({
  transcript,
  onSaveTranscript,
  isSaving = false,
}: TranscriptViewerProps) {
  const initialText = transcript.edited_text || transcript.original_text;
  const [text, setText] = useState(initialText);
  const [savedNotice, setSavedNotice] = useState(false);

  useEffect(() => {
    setText(transcript.edited_text || transcript.original_text);
  }, [transcript.edited_text, transcript.original_text]);

  const isDirty = text.trim() !== initialText.trim();

  const handleSave = async () => {
    await onSaveTranscript(text);
    setSavedNotice(true);
    window.setTimeout(() => setSavedNotice(false), 2500);
  };

  const handleRestoreOriginal = () => {
    setText(transcript.original_text);
  };

  return (
    <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h3 className="text-base font-semibold text-slate-900">Consultation Transcript</h3>
          <Badge variant="secondary">{transcript.language || "en"}</Badge>
          {transcript.is_mock && (
            <Badge variant="warning">Dev Mock Output</Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          {text !== transcript.original_text && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleRestoreOriginal}
              disabled={isSaving}
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Reset to Original</span>
            </Button>
          )}
          <Button
            type="button"
            size="sm"
            onClick={handleSave}
            disabled={isSaving || !isDirty || !text.trim()}
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
                <span>Save Transcript Edits</span>
              </>
            )}
          </Button>
        </div>
      </div>

      <Textarea
        aria-label="Editable consultation transcript"
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={12}
        className="font-normal leading-relaxed"
      />

      <p className="text-xs text-slate-500">
        The original unedited speech-to-text output is preserved separately for auditability.
      </p>
    </div>
  );
}

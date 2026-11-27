import { Volume2 } from "lucide-react";
import { formatDuration } from "@/lib/utils";

interface AudioPlayerProps {
  src: string;
  durationSeconds?: number;
}

export function AudioPlayer({ src, durationSeconds }: AudioPlayerProps) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3.5">
      <div className="mb-2 flex items-center justify-between text-xs font-medium text-slate-600">
        <span className="flex items-center gap-1.5">
          <Volume2 className="h-4 w-4 text-primary" />
          <span>Recorded Consultation Playback</span>
        </span>
        {typeof durationSeconds === "number" && (
          <span className="tabular-nums">{formatDuration(durationSeconds)}</span>
        )}
      </div>
      <audio controls src={src} className="w-full" preload="metadata" />
    </div>
  );
}

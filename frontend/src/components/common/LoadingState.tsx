import { Loader2 } from "lucide-react";

export function LoadingState({ message = "Loading..." }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-slate-200 bg-white py-14 text-center">
      <Loader2 className="h-7 w-7 animate-spin text-primary" />
      <p className="mt-3 text-sm font-medium text-slate-600">{message}</p>
    </div>
  );
}

import { AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export function ErrorState({
  title = "Unable to load data",
  message,
  onRetry,
}: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-red-200 bg-red-50/60 px-6 py-10 text-center">
      <AlertCircle className="h-7 w-7 text-red-600" />
      <h3 className="mt-3 text-base font-semibold text-red-900">{title}</h3>
      <p className="mt-1 max-w-md text-sm text-red-700">{message}</p>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry} className="mt-4">
          <RefreshCw className="h-4 w-4" />
          <span>Retry</span>
        </Button>
      )}
    </div>
  );
}

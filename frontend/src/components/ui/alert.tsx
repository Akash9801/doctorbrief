import * as React from "react";
import { AlertCircle, CheckCircle2, Info, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "destructive" | "warning" | "success";
  title?: string;
}

export function Alert({ className, variant = "default", title, children, ...props }: AlertProps) {
  const styles = {
    default: "border-slate-200 bg-slate-50 text-slate-800",
    destructive: "border-red-200 bg-red-50 text-red-900",
    warning: "border-amber-200 bg-amber-50 text-amber-900",
    success: "border-emerald-200 bg-emerald-50 text-emerald-900",
  }[variant];

  const Icon = {
    default: Info,
    destructive: AlertCircle,
    warning: AlertTriangle,
    success: CheckCircle2,
  }[variant];

  return (
    <div
      role="alert"
      className={cn("flex gap-3 rounded-lg border p-3.5 text-sm", styles, className)}
      {...props}
    >
      <Icon className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="space-y-1">
        {title && <p className="font-semibold leading-tight">{title}</p>}
        <div className="text-sm opacity-95">{children}</div>
      </div>
    </div>
  );
}

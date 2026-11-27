import { Badge } from "@/components/ui/badge";

const STATUS_MAP: Record<string, { label: string; variant: "default" | "secondary" | "success" | "warning" | "destructive" | "info" }> = {
  IN_PROGRESS: { label: "In Progress", variant: "info" },
  TRANSCRIBED: { label: "Transcribed", variant: "info" },
  EXTRACTED: { label: "Extracted", variant: "default" },
  COMPLETED: { label: "Completed", variant: "success" },
  DRAFT: { label: "Draft", variant: "warning" },
  UNDER_REVIEW: { label: "Under Review", variant: "info" },
  APPROVED: { label: "Approved", variant: "success" },
  GRANTED: { label: "Consent Granted", variant: "success" },
  PENDING: { label: "Pending", variant: "warning" },
  FAILED: { label: "Failed", variant: "destructive" },
  NONE: { label: "Not Started", variant: "secondary" },
};

export function StatusBadge({ status }: { status?: string | null }) {
  const key = (status || "NONE").toUpperCase();
  const config = STATUS_MAP[key] || { label: key.replace(/_/g, " "), variant: "secondary" as const };
  return <Badge variant={config.variant}>{config.label}</Badge>;
}

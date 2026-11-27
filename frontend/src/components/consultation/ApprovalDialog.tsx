import { CheckCircle2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface ApprovalDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  patientName: string;
  missingInfoCount: number;
  onConfirmApprove: () => Promise<void>;
  isApproving: boolean;
}

export function ApprovalDialog({
  open,
  onOpenChange,
  patientName,
  missingInfoCount,
  onConfirmApprove,
  isApproving,
}: ApprovalDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Approve Clinical Note</DialogTitle>
          <DialogDescription>
            Confirm that you have reviewed the SOAP note for <strong>{patientName}</strong> and
            verified all clinical details against the consultation.
          </DialogDescription>
        </DialogHeader>

        {missingInfoCount > 0 && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            Note: {missingInfoCount} documentation gap{missingInfoCount === 1 ? " was" : "s were"}{" "}
            flagged during AI extraction. Please confirm you have added or verified any necessary
            details before finalizing.
          </div>
        )}

        <p className="text-xs text-slate-500">
          Once approved, this note is locked with your doctor ID and timestamp, and added to the
          patient&apos;s clinical history. Any later changes will create a new versioned amendment.
        </p>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isApproving}
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="success"
            onClick={onConfirmApprove}
            disabled={isApproving}
          >
            {isApproving ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Approving...</span>
              </>
            ) : (
              <>
                <CheckCircle2 className="h-4 w-4" />
                <span>Confirm & Approve Note</span>
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

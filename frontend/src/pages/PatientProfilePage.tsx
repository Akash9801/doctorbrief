import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Edit3, Mic, FileText, Loader2 } from "lucide-react";
import { consultationsApi, patientsApi } from "@/services/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { PatientDetailsCard } from "@/components/patients/PatientDetailsCard";
import { StatusBadge } from "@/components/common/StatusBadge";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { formatDateTime } from "@/lib/utils";

export function PatientProfilePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [editOpen, setEditOpen] = useState(false);

  const patientQuery = useQuery({
    queryKey: ["patient", id],
    queryFn: () => patientsApi.get(id!),
    enabled: Boolean(id),
  });

  const historyQuery = useQuery({
    queryKey: ["patient-history", id],
    queryFn: () => patientsApi.history(id!),
    enabled: Boolean(id),
  });

  const [editForm, setEditForm] = useState({
    full_name: "",
    age: "",
    gender: "Female",
    phone: "",
    medical_history: "",
    allergies: "",
  });

  const openEditModal = () => {
    if (!patientQuery.data) return;
    const p = patientQuery.data;
    setEditForm({
      full_name: p.full_name,
      age: p.age !== null && p.age !== undefined ? String(p.age) : "",
      gender: p.gender,
      phone: p.phone,
      medical_history: p.medical_history || "",
      allergies: p.allergies || "",
    });
    setEditOpen(true);
  };

  const updateMutation = useMutation({
    mutationFn: () =>
      patientsApi.update(id!, {
        full_name: editForm.full_name,
        age: editForm.age ? Number(editForm.age) : null,
        gender: editForm.gender,
        phone: editForm.phone,
        medical_history: editForm.medical_history,
        allergies: editForm.allergies,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["patient", id] });
      await queryClient.invalidateQueries({ queryKey: ["patients"] });
      setEditOpen(false);
    },
  });

  const startConsultMutation = useMutation({
    mutationFn: () =>
      consultationsApi.create({ patient_id: id!, consent_status: "PENDING" }),
    onSuccess: (consultation) => {
      navigate(`/consultations/${consultation.id}/record`);
    },
  });

  if (patientQuery.isLoading) {
    return <LoadingState message="Loading patient profile..." />;
  }

  if (patientQuery.isError || !patientQuery.data) {
    return (
      <ErrorState
        message={(patientQuery.error as Error)?.message || "Patient record could not be loaded."}
        onRetry={() => patientQuery.refetch()}
      />
    );
  }

  const patient = patientQuery.data;
  const history = historyQuery.data || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button asChild variant="ghost" size="sm">
          <Link to="/patients">
            <ArrowLeft className="h-4 w-4" />
            <span>Back to Patients</span>
          </Link>
        </Button>
        <div className="flex items-center gap-2.5">
          <Button type="button" variant="outline" onClick={openEditModal}>
            <Edit3 className="h-4 w-4" />
            <span>Edit Patient</span>
          </Button>
          <Button
            type="button"
            onClick={() => startConsultMutation.mutate()}
            disabled={startConsultMutation.isPending}
          >
            {startConsultMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Mic className="h-4 w-4" />
            )}
            <span>Start Consultation</span>
          </Button>
        </div>
      </div>

      <PatientDetailsCard patient={patient} />

      <Card>
        <CardHeader>
          <CardTitle>Consultation & Approved Note History</CardTitle>
          <CardDescription>
            Previous consultations and clinical notes documented for {patient.full_name}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {historyQuery.isLoading ? (
            <LoadingState message="Loading consultation history..." />
          ) : history.length === 0 ? (
            <EmptyState
              icon={FileText}
              title="No consultations yet"
              description="Start a new consultation to record, transcribe, and generate a SOAP note."
            />
          ) : (
            <div className="space-y-4">
              {history.map((c) => {
                const approvedNote =
                  c.note_versions.find((n) => n.status === "APPROVED") || c.latest_note;
                return (
                  <div
                    key={c.id}
                    className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 space-y-3"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-semibold text-slate-900">
                          {formatDateTime(c.started_at)}
                        </span>
                        <StatusBadge status={c.status} />
                        {c.latest_note && <StatusBadge status={c.latest_note.status} />}
                      </div>
                      <Button asChild variant="outline" size="sm">
                        <Link
                          to={
                            c.latest_note
                              ? `/consultations/${c.id}/note`
                              : c.transcript
                              ? `/consultations/${c.id}/transcript`
                              : `/consultations/${c.id}/record`
                          }
                        >
                          Open Consultation
                        </Link>
                      </Button>
                    </div>

                    {approvedNote ? (
                      <div className="grid grid-cols-1 gap-3 rounded-lg border border-slate-200 bg-white p-3.5 text-sm sm:grid-cols-2">
                        <div>
                          <p className="text-xs font-semibold uppercase text-slate-500">
                            Subjective
                          </p>
                          <p className="mt-1 whitespace-pre-wrap text-slate-800">
                            {approvedNote.subjective}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs font-semibold uppercase text-slate-500">
                            Objective
                          </p>
                          <p className="mt-1 whitespace-pre-wrap text-slate-800">
                            {approvedNote.objective}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs font-semibold uppercase text-slate-500">
                            Assessment
                          </p>
                          <p className="mt-1 whitespace-pre-wrap text-slate-800">
                            {approvedNote.assessment}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs font-semibold uppercase text-slate-500">Plan</p>
                          <p className="mt-1 whitespace-pre-wrap text-slate-800">
                            {approvedNote.plan}
                          </p>
                        </div>
                      </div>
                    ) : (
                      <p className="text-xs text-slate-500">
                        No SOAP note generated for this consultation yet.
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Patient Information</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1">
              <Label>Full Name</Label>
              <Input
                value={editForm.full_name}
                onChange={(e) => setEditForm((f) => ({ ...f, full_name: e.target.value }))}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>Age</Label>
                <Input
                  type="number"
                  value={editForm.age}
                  onChange={(e) => setEditForm((f) => ({ ...f, age: e.target.value }))}
                />
              </div>
              <div className="space-y-1">
                <Label>Gender</Label>
                <select
                  value={editForm.gender}
                  onChange={(e) => setEditForm((f) => ({ ...f, gender: e.target.value }))}
                  className="flex h-10 w-full rounded-lg border border-input bg-white px-3 text-sm"
                >
                  <option value="Female">Female</option>
                  <option value="Male">Male</option>
                  <option value="Other">Other</option>
                </select>
              </div>
            </div>
            <div className="space-y-1">
              <Label>Phone</Label>
              <Input
                value={editForm.phone}
                onChange={(e) => setEditForm((f) => ({ ...f, phone: e.target.value }))}
              />
            </div>
            <div className="space-y-1">
              <Label>Medical History</Label>
              <Textarea
                rows={2}
                value={editForm.medical_history}
                onChange={(e) =>
                  setEditForm((f) => ({ ...f, medical_history: e.target.value }))
                }
              />
            </div>
            <div className="space-y-1">
              <Label>Allergies</Label>
              <Textarea
                rows={2}
                value={editForm.allergies}
                onChange={(e) => setEditForm((f) => ({ ...f, allergies: e.target.value }))}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => updateMutation.mutate()} disabled={updateMutation.isPending}>
              {updateMutation.isPending ? "Saving..." : "Save Changes"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

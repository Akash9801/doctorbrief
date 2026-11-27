import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Search, Mic, UserPlus, Loader2, Check } from "lucide-react";
import { consultationsApi, patientsApi } from "@/services/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";
import { LoadingState } from "@/components/common/LoadingState";

export function NewConsultationPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [selectedPatientId, setSelectedPatientId] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const patientsQuery = useQuery({
    queryKey: ["patients", search],
    queryFn: () => patientsApi.list({ search: search.trim() || undefined }),
  });

  const createConsultation = useMutation({
    mutationFn: (patientId: string) =>
      consultationsApi.create({ patient_id: patientId, consent_status: "PENDING" }),
    onSuccess: (consultation) => {
      navigate(`/consultations/${consultation.id}/record`);
    },
    onError: (err: Error) => {
      setErrorMessage(err.message || "Unable to create consultation.");
    },
  });

  const patients = patientsQuery.data || [];

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Start New Consultation</h2>
          <p className="text-sm text-slate-500">
            Select an existing patient or register a new patient before recording.
          </p>
        </div>
        <Button asChild variant="outline">
          <Link to="/patients/new">
            <UserPlus className="h-4 w-4" />
            <span>Register New Patient</span>
          </Link>
        </Button>
      </div>

      {errorMessage && <Alert variant="destructive">{errorMessage}</Alert>}

      <Card>
        <CardHeader>
          <CardTitle>Select Patient</CardTitle>
          <CardDescription>
            Choose who this consultation belongs to. You will confirm patient consent on the next
            screen before recording.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search patients by name, ID, or phone..."
              className="pl-9"
            />
          </div>

          {patientsQuery.isLoading ? (
            <LoadingState message="Loading patients..." />
          ) : patients.length === 0 ? (
            <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center">
              <p className="text-sm text-slate-600">
                No matching patients found. Add a patient to begin.
              </p>
              <Button asChild className="mt-4" size="sm">
                <Link to="/patients/new">Add Patient</Link>
              </Button>
            </div>
          ) : (
            <div className="max-h-80 space-y-2 overflow-y-auto pr-1">
              {patients.map((patient) => {
                const selected = selectedPatientId === patient.id;
                return (
                  <button
                    key={patient.id}
                    type="button"
                    onClick={() => setSelectedPatientId(patient.id)}
                    className={`flex w-full items-center justify-between rounded-lg border p-3.5 text-left transition-colors ${
                      selected
                        ? "border-primary bg-primary/5"
                        : "border-slate-200 bg-white hover:bg-slate-50"
                    }`}
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-semibold text-primary">
                          {patient.patient_code}
                        </span>
                        <span className="font-semibold text-slate-900">{patient.full_name}</span>
                      </div>
                      <p className="mt-0.5 text-xs text-slate-500">
                        {patient.age ?? "—"} yrs · {patient.gender} · {patient.phone}
                      </p>
                    </div>
                    {selected && (
                      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-white">
                        <Check className="h-3.5 w-3.5" />
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          )}

          <div className="flex justify-end pt-2">
            <Button
              type="button"
              size="lg"
              disabled={!selectedPatientId || createConsultation.isPending}
              onClick={() => createConsultation.mutate(selectedPatientId)}
            >
              {createConsultation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Starting Consultation...</span>
                </>
              ) : (
                <>
                  <Mic className="h-4 w-4" />
                  <span>Proceed to Recording</span>
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

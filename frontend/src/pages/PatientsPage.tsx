import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { Search, UserPlus, Users } from "lucide-react";
import { consultationsApi, patientsApi } from "@/services/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { PatientTable } from "@/components/patients/PatientTable";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";

export function PatientsPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [gender, setGender] = useState("all");

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["patients", search, gender],
    queryFn: () => patientsApi.list({ search: search.trim() || undefined, gender }),
  });

  const startConsultMutation = useMutation({
    mutationFn: (patientId: string) =>
      consultationsApi.create({ patient_id: patientId, consent_status: "PENDING" }),
    onSuccess: (consultation) => {
      navigate(`/consultations/${consultation.id}/record`);
    },
  });

  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Patients</h2>
          <p className="text-sm text-slate-500">
            Search, manage, and open patient clinical records.
          </p>
        </div>
        <Button asChild>
          <Link to="/patients/new">
            <UserPlus className="h-4 w-4" />
            <span>Add Patient</span>
          </Link>
        </Button>
      </div>

      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:flex-row">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by patient name, ID (e.g. DB-0001), or phone..."
            className="pl-9"
          />
        </div>
        <select
          aria-label="Filter by gender"
          value={gender}
          onChange={(e) => setGender(e.target.value)}
          className="h-10 rounded-lg border border-input bg-white px-3 text-sm text-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <option value="all">All Genders</option>
          <option value="Female">Female</option>
          <option value="Male">Male</option>
          <option value="Other">Other</option>
        </select>
      </div>

      {isLoading ? (
        <LoadingState message="Loading patient directory..." />
      ) : isError ? (
        <ErrorState
          message={(error as Error)?.message || "Failed to load patients."}
          onRetry={() => refetch()}
        />
      ) : !data || data.length === 0 ? (
        <EmptyState
          icon={Users}
          title={search || gender !== "all" ? "No matching patients found" : "No patients yet"}
          description={
            search || gender !== "all"
              ? "Try clearing your search or filter criteria."
              : "Register your first patient to start voice-assisted clinical documentation."
          }
          action={
            <Button asChild>
              <Link to="/patients/new">Add First Patient</Link>
            </Button>
          }
        />
      ) : (
        <PatientTable
          patients={data}
          onStartConsultation={(patientId) => startConsultMutation.mutate(patientId)}
        />
      )}
    </div>
  );
}

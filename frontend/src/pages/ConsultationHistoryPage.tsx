import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Search, History, Plus } from "lucide-react";
import { consultationsApi, patientsApi } from "@/services/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/common/StatusBadge";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { formatDateTime } from "@/lib/utils";

export function ConsultationHistoryPage() {
  const [search, setSearch] = useState("");
  const [patientId, setPatientId] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const patientsQuery = useQuery({
    queryKey: ["patients", "all-filter"],
    queryFn: () => patientsApi.list(),
  });

  const consultationsQuery = useQuery({
    queryKey: ["consultations", search, patientId, dateFrom, dateTo],
    queryFn: () =>
      consultationsApi.list({
        search: search.trim() || undefined,
        patient_id: patientId || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      }),
  });

  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Consultation History</h2>
          <p className="text-sm text-slate-500">
            Search past consultations, transcripts, and approved clinical notes.
          </p>
        </div>
        <Button asChild>
          <Link to="/consultations/new">
            <Plus className="h-4 w-4" />
            <span>New Consultation</span>
          </Link>
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search patient name or ID..."
            className="pl-9"
          />
        </div>

        <select
          aria-label="Filter by patient"
          value={patientId}
          onChange={(e) => setPatientId(e.target.value)}
          className="h-10 rounded-lg border border-input bg-white px-3 text-sm text-slate-700"
        >
          <option value="">All Patients</option>
          {(patientsQuery.data || []).map((p) => (
            <option key={p.id} value={p.id}>
              {p.full_name} ({p.patient_code})
            </option>
          ))}
        </select>

        <Input
          type="date"
          aria-label="Filter from date"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
        />

        <Input
          type="date"
          aria-label="Filter to date"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
        />
      </div>

      {consultationsQuery.isLoading ? (
        <LoadingState message="Loading consultation history..." />
      ) : consultationsQuery.isError ? (
        <ErrorState
          message={(consultationsQuery.error as Error)?.message || "Failed to load consultations."}
          onRetry={() => consultationsQuery.refetch()}
        />
      ) : !consultationsQuery.data || consultationsQuery.data.length === 0 ? (
        <EmptyState
          icon={History}
          title="No consultations found"
          description="No consultations match your current filters."
          action={
            <Button asChild>
              <Link to="/consultations/new">Start New Consultation</Link>
            </Button>
          }
        />
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wider text-slate-600">
                <tr>
                  <th className="px-4 py-3">Patient</th>
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Doctor</th>
                  <th className="px-4 py-3">Consultation</th>
                  <th className="px-4 py-3">Transcript</th>
                  <th className="px-4 py-3">SOAP Note</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {consultationsQuery.data.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50/70">
                    <td className="px-4 py-3">
                      <Link
                        to={`/patients/${item.patient_id}`}
                        className="font-medium text-slate-900 hover:text-primary hover:underline"
                      >
                        {item.patient_name}
                      </Link>
                      <div className="font-mono text-xs text-slate-500">{item.patient_code}</div>
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {formatDateTime(item.started_at)}
                    </td>
                    <td className="px-4 py-3 text-slate-600">{item.doctor_name}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={item.status} />
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={item.transcription_status} />
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={item.note_status} />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-2">
                        {item.transcription_status === "COMPLETED" && (
                          <Button asChild variant="ghost" size="sm">
                            <Link to={`/consultations/${item.id}/transcript`}>Transcript</Link>
                          </Button>
                        )}
                        <Button asChild variant="outline" size="sm">
                          <Link
                            to={
                              item.note_status && item.note_status !== "NONE"
                                ? `/consultations/${item.id}/note`
                                : item.transcription_status === "COMPLETED"
                                ? `/consultations/${item.id}/transcript`
                                : `/consultations/${item.id}/record`
                            }
                          >
                            Open
                          </Link>
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

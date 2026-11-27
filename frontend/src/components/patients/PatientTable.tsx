import { Link } from "react-router-dom";
import { Eye, Mic } from "lucide-react";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/utils";
import type { Patient } from "@/types/api";

interface PatientTableProps {
  patients: Patient[];
  onStartConsultation?: (patientId: string) => void;
}

export function PatientTable({ patients, onStartConsultation }: PatientTableProps) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wider text-slate-600">
            <tr>
              <th className="px-4 py-3">Patient ID</th>
              <th className="px-4 py-3">Full Name</th>
              <th className="px-4 py-3">Age / Gender</th>
              <th className="px-4 py-3">Phone</th>
              <th className="px-4 py-3">Consultations</th>
              <th className="px-4 py-3">Registered</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {patients.map((patient) => (
              <tr key={patient.id} className="hover:bg-slate-50/70">
                <td className="px-4 py-3 font-mono text-xs font-semibold text-primary">
                  {patient.patient_code}
                </td>
                <td className="px-4 py-3 font-medium text-slate-900">
                  <Link to={`/patients/${patient.id}`} className="hover:text-primary hover:underline">
                    {patient.full_name}
                  </Link>
                </td>
                <td className="px-4 py-3 text-slate-600">
                  {patient.age !== null && patient.age !== undefined ? `${patient.age} yrs` : "—"} ·{" "}
                  {patient.gender}
                </td>
                <td className="px-4 py-3 text-slate-600">{patient.phone}</td>
                <td className="px-4 py-3 tabular-nums text-slate-700">
                  {patient.consultation_count}
                </td>
                <td className="px-4 py-3 text-slate-500">{formatDate(patient.created_at)}</td>
                <td className="px-4 py-3">
                  <div className="flex justify-end gap-2">
                    <Button asChild variant="outline" size="sm">
                      <Link to={`/patients/${patient.id}`}>
                        <Eye className="h-3.5 w-3.5" />
                        <span>Profile</span>
                      </Link>
                    </Button>
                    {onStartConsultation && (
                      <Button
                        type="button"
                        size="sm"
                        onClick={() => onStartConsultation(patient.id)}
                      >
                        <Mic className="h-3.5 w-3.5" />
                        <span>Consult</span>
                      </Button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

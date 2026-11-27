import { AlertTriangle, Phone, User, Calendar } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";
import type { Patient } from "@/types/api";

export function PatientDetailsCard({ patient }: { patient: Patient }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-3">
        <div>
          <Badge variant="default" className="mb-2 font-mono">
            {patient.patient_code}
          </Badge>
          <CardTitle className="text-xl">{patient.full_name}</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
          <div className="flex items-center gap-2 text-slate-600">
            <User className="h-4 w-4 text-slate-400" />
            <span>
              {patient.age !== null && patient.age !== undefined ? `${patient.age} years` : "Age N/A"} ·{" "}
              {patient.gender}
            </span>
          </div>
          <div className="flex items-center gap-2 text-slate-600">
            <Phone className="h-4 w-4 text-slate-400" />
            <span>{patient.phone}</span>
          </div>
          <div className="flex items-center gap-2 text-slate-600">
            <Calendar className="h-4 w-4 text-slate-400" />
            <span>
              {patient.date_of_birth ? `DOB: ${formatDate(patient.date_of_birth)}` : `Added ${formatDate(patient.created_at)}`}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 pt-1 sm:grid-cols-2">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Medical History
            </p>
            <p className="mt-1 text-sm text-slate-800">
              {patient.medical_history || "No chronic medical history recorded."}
            </p>
          </div>
          <div className="rounded-lg border border-amber-200 bg-amber-50/70 p-3">
            <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-amber-800">
              <AlertTriangle className="h-3.5 w-3.5" />
              <span>Known Allergies</span>
            </p>
            <p className="mt-1 text-sm text-amber-950">
              {patient.allergies || "No known allergies recorded."}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

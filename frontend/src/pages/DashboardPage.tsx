import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  Users,
  Stethoscope,
  CalendarCheck,
  FileClock,
  Mic,
  UserPlus,
  History,
  ArrowRight,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import { useAuth } from "@/contexts/AuthContext";
import { dashboardApi } from "@/services/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/common/StatusBadge";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { formatDateTime } from "@/lib/utils";

export function DashboardPage() {
  const { doctor } = useAuth();
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["dashboard"],
    queryFn: dashboardApi.get,
  });

  const todayLabel = new Date().toLocaleDateString("en-IN", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  if (isLoading) {
    return <LoadingState message="Loading clinic dashboard..." />;
  }

  if (isError || !data) {
    return (
      <ErrorState
        message={(error as Error)?.message || "Could not load dashboard metrics."}
        onRetry={() => refetch()}
      />
    );
  }

  const statCards = [
    {
      label: "Total Patients",
      value: data.stats.total_patients,
      icon: Users,
      tone: "bg-sky-50 text-sky-700",
    },
    {
      label: "Total Consultations",
      value: data.stats.total_consultations,
      icon: Stethoscope,
      tone: "bg-primary/10 text-primary",
    },
    {
      label: "Completed This Month",
      value: data.stats.consultations_this_month,
      icon: CalendarCheck,
      tone: "bg-emerald-50 text-emerald-700",
    },
    {
      label: "Notes Awaiting Approval",
      value: data.stats.notes_awaiting_approval,
      icon: FileClock,
      tone: "bg-amber-50 text-amber-700",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm sm:flex-row sm:items-center">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
            {todayLabel}
          </p>
          <h2 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
            Welcome back, {doctor?.full_name}
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Focus on the patient. Let DoctorBrief handle the documentation.
          </p>
        </div>
        <div className="flex flex-wrap gap-2.5">
          <Button asChild size="lg">
            <Link to="/consultations/new">
              <Mic className="h-4 w-4" />
              <span>Start New Consultation</span>
            </Link>
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map((card) => {
          const Icon = card.icon;
          return (
            <Card key={card.label}>
              <CardContent className="flex items-center justify-between p-5">
                <div>
                  <p className="text-xs font-medium text-slate-500">{card.label}</p>
                  <p className="mt-1.5 tabular-nums text-3xl font-bold text-slate-900">
                    {card.value}
                  </p>
                </div>
                <div className={`flex h-11 w-11 items-center justify-center rounded-xl ${card.tone}`}>
                  <Icon className="h-5 w-5" />
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Consultation Activity (Last 7 Days)</CardTitle>
            <CardDescription>
              Daily consultations started and clinical notes approved
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.activity_last_7_days} margin={{ top: 8, right: 12, left: -16, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                  <XAxis dataKey="label" tick={{ fontSize: 12, fill: "#64748B" }} axisLine={false} tickLine={false} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: "#64748B" }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      borderRadius: "0.5rem",
                      border: "1px solid #E2E8F0",
                      fontSize: "12px",
                    }}
                  />
                  <Bar dataKey="consultations" name="Consultations" fill="#0F4C5C" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="approved_notes" name="Approved Notes" fill="#15803D" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>Common clinic workflows</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2.5">
            <Button asChild className="w-full justify-between" variant="default">
              <Link to="/consultations/new">
                <span className="flex items-center gap-2">
                  <Mic className="h-4 w-4" />
                  <span>New Consultation</span>
                </span>
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button asChild className="w-full justify-between" variant="outline">
              <Link to="/patients/new">
                <span className="flex items-center gap-2">
                  <UserPlus className="h-4 w-4" />
                  <span>Add Patient</span>
                </span>
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button asChild className="w-full justify-between" variant="outline">
              <Link to="/patients">
                <span className="flex items-center gap-2">
                  <Users className="h-4 w-4" />
                  <span>View Patients</span>
                </span>
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button asChild className="w-full justify-between" variant="outline">
              <Link to="/consultations">
                <span className="flex items-center gap-2">
                  <History className="h-4 w-4" />
                  <span>Consultation History</span>
                </span>
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Recent Consultations</CardTitle>
            <CardDescription>Open any consultation to continue recording, review, or approve notes</CardDescription>
          </div>
          <Button asChild variant="ghost" size="sm">
            <Link to="/consultations">View all</Link>
          </Button>
        </CardHeader>
        <CardContent>
          {data.recent_consultations.length === 0 ? (
            <EmptyState
              icon={Stethoscope}
              title="No consultations recorded yet"
              description="Add a patient and start your first voice-assisted consultation."
              action={
                <Button asChild>
                  <Link to="/consultations/new">Start First Consultation</Link>
                </Button>
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-200 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  <tr>
                    <th className="pb-3 pr-4">Patient</th>
                    <th className="pb-3 pr-4">Date</th>
                    <th className="pb-3 pr-4">Consultation Status</th>
                    <th className="pb-3 pr-4">Note Status</th>
                    <th className="pb-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.recent_consultations.map((item) => {
                    const targetRoute =
                      item.note_status && item.note_status !== "NONE"
                        ? `/consultations/${item.id}/note`
                        : item.consultation_status === "TRANSCRIBED" ||
                          item.consultation_status === "EXTRACTED"
                        ? `/consultations/${item.id}/transcript`
                        : `/consultations/${item.id}/record`;
                    return (
                      <tr key={item.id} className="hover:bg-slate-50/70">
                        <td className="py-3 pr-4">
                          <div className="font-medium text-slate-900">{item.patient_name}</div>
                          <div className="font-mono text-xs text-slate-500">{item.patient_code}</div>
                        </td>
                        <td className="py-3 pr-4 text-slate-600">
                          {formatDateTime(item.consultation_date)}
                        </td>
                        <td className="py-3 pr-4">
                          <StatusBadge status={item.consultation_status} />
                        </td>
                        <td className="py-3 pr-4">
                          <StatusBadge status={item.note_status} />
                        </td>
                        <td className="py-3 text-right">
                          <Button asChild variant="outline" size="sm">
                            <Link to={targetRoute}>Open</Link>
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

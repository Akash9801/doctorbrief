import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Loader2, UserPlus } from "lucide-react";
import { ApiError, patientsApi } from "@/services/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Alert } from "@/components/ui/alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const patientSchema = z
  .object({
    full_name: z.string().min(2, "Patient full name is required."),
    age: z.string().optional(),
    date_of_birth: z.string().optional(),
    gender: z.string().min(1, "Gender is required."),
    phone: z.string().min(7, "Phone number must be at least 7 characters."),
    medical_history: z.string().optional(),
    allergies: z.string().optional(),
  })
  .refine((data) => Boolean(data.age?.trim() || data.date_of_birth?.trim()), {
    message: "Provide either age or date of birth.",
    path: ["age"],
  });

type PatientFormValues = z.infer<typeof patientSchema>;

export function AddPatientPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<PatientFormValues>({
    resolver: zodResolver(patientSchema),
    defaultValues: {
      gender: "Female",
    },
  });

  const onSubmit = async (values: PatientFormValues) => {
    setServerError(null);
    try {
      const parsedAge = values.age?.trim() ? Number(values.age.trim()) : null;
      const created = await patientsApi.create({
        full_name: values.full_name,
        age: parsedAge !== null && !Number.isNaN(parsedAge) ? parsedAge : null,
        date_of_birth: values.date_of_birth?.trim() ? values.date_of_birth.trim() : null,
        gender: values.gender,
        phone: values.phone,
        medical_history: values.medical_history || undefined,
        allergies: values.allergies || undefined,
      });
      await queryClient.invalidateQueries({ queryKey: ["patients"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      navigate(`/patients/${created.id}`);
    } catch (err) {
      setServerError(
        err instanceof ApiError ? err.message : "Failed to create patient record."
      );
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <div className="flex items-center gap-3">
        <Button asChild variant="ghost" size="sm">
          <Link to="/patients">
            <ArrowLeft className="h-4 w-4" />
            <span>Back to Patients</span>
          </Link>
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Add New Patient</CardTitle>
          <CardDescription>
            A unique Patient ID (e.g., DB-0001) will be automatically generated.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {serverError && <Alert variant="destructive">{serverError}</Alert>}

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="full_name">Full Name</Label>
                <Input id="full_name" placeholder="Meera Nair" {...register("full_name")} />
                {errors.full_name && (
                  <p className="text-xs text-red-600">{errors.full_name.message}</p>
                )}
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="age">Age (Years)</Label>
                <Input id="age" type="number" min={0} max={130} placeholder="42" {...register("age")} />
                {errors.age && (
                  <p className="text-xs text-red-600">{errors.age.message}</p>
                )}
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="date_of_birth">Date of Birth (Optional)</Label>
                <Input id="date_of_birth" type="date" {...register("date_of_birth")} />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="gender">Gender</Label>
                <select
                  id="gender"
                  {...register("gender")}
                  className="flex h-10 w-full rounded-lg border border-input bg-white px-3 py-2 text-sm text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <option value="Female">Female</option>
                  <option value="Male">Male</option>
                  <option value="Other">Other</option>
                </select>
                {errors.gender && (
                  <p className="text-xs text-red-600">{errors.gender.message}</p>
                )}
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="phone">Phone Number</Label>
                <Input id="phone" placeholder="+91 9811122233" {...register("phone")} />
                {errors.phone && (
                  <p className="text-xs text-red-600">{errors.phone.message}</p>
                )}
              </div>

              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="medical_history">Relevant Medical History (Optional)</Label>
                <Textarea
                  id="medical_history"
                  rows={3}
                  placeholder="Type 2 Diabetes (diagnosed 2021), Hypertension..."
                  {...register("medical_history")}
                />
              </div>

              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="allergies">Known Allergies (Optional)</Label>
                <Textarea
                  id="allergies"
                  rows={2}
                  placeholder="Penicillin, Sulfa drugs..."
                  {...register("allergies")}
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <Button asChild variant="outline" type="button">
                <Link to="/patients">Cancel</Link>
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Saving Patient...</span>
                  </>
                ) : (
                  <>
                    <UserPlus className="h-4 w-4" />
                    <span>Create Patient</span>
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

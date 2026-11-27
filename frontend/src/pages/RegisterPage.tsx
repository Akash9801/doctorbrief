import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Stethoscope, Loader2 } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { ApiError } from "@/services/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert } from "@/components/ui/alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const registerSchema = z
  .object({
    full_name: z.string().min(2, "Full name must be at least 2 characters."),
    email: z.string().email("Enter a valid email address."),
    password: z.string().min(8, "Password must be at least 8 characters."),
    confirm_password: z.string(),
    specialty: z.string().optional(),
    clinic_name: z.string().optional(),
    phone: z.string().optional(),
    registration_number: z.string().optional(),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Passwords do not match.",
    path: ["confirm_password"],
  });

type RegisterFormValues = z.infer<typeof registerSchema>;

export function RegisterPage() {
  const { register: registerDoctor } = useAuth();
  const navigate = useNavigate();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (values: RegisterFormValues) => {
    setServerError(null);
    try {
      await registerDoctor({
        full_name: values.full_name,
        email: values.email,
        password: values.password,
        specialty: values.specialty || undefined,
        clinic_name: values.clinic_name || undefined,
        phone: values.phone || undefined,
        registration_number: values.registration_number || undefined,
      });
      navigate("/", { replace: true });
    } catch (err) {
      setServerError(
        err instanceof ApiError ? err.message : "Registration failed. Please try again."
      );
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-10">
      <div className="w-full max-w-lg space-y-6">
        <div className="flex flex-col items-center text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-white shadow-sm">
            <Stethoscope className="h-6 w-6" />
          </div>
          <h1 className="mt-4 text-2xl font-bold tracking-tight text-slate-900">
            Create DoctorBrief Account
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Voice-first clinical documentation assistant for doctors and clinics.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Doctor Registration</CardTitle>
            <CardDescription>
              Set up your clinical profile to start documenting consultations.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              {serverError && <Alert variant="destructive">{serverError}</Alert>}

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="space-y-1.5 sm:col-span-2">
                  <Label htmlFor="full_name">Full Name</Label>
                  <Input
                    id="full_name"
                    placeholder="Dr. Ananya Sharma"
                    {...register("full_name")}
                  />
                  {errors.full_name && (
                    <p className="text-xs text-red-600">{errors.full_name.message}</p>
                  )}
                </div>

                <div className="space-y-1.5 sm:col-span-2">
                  <Label htmlFor="email">Email Address</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="dr.sharma@clinic.in"
                    {...register("email")}
                  />
                  {errors.email && (
                    <p className="text-xs text-red-600">{errors.email.message}</p>
                  )}
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="password">Password</Label>
                  <Input id="password" type="password" {...register("password")} />
                  {errors.password && (
                    <p className="text-xs text-red-600">{errors.password.message}</p>
                  )}
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="confirm_password">Confirm Password</Label>
                  <Input
                    id="confirm_password"
                    type="password"
                    {...register("confirm_password")}
                  />
                  {errors.confirm_password && (
                    <p className="text-xs text-red-600">{errors.confirm_password.message}</p>
                  )}
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="specialty">Specialty (Optional)</Label>
                  <Input
                    id="specialty"
                    placeholder="General Medicine"
                    {...register("specialty")}
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="clinic_name">Clinic Name (Optional)</Label>
                  <Input
                    id="clinic_name"
                    placeholder="Swasthya Care Clinic"
                    {...register("clinic_name")}
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="phone">Phone (Optional)</Label>
                  <Input id="phone" placeholder="+91 9876543210" {...register("phone")} />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="registration_number">Medical Reg. No. (Optional)</Label>
                  <Input
                    id="registration_number"
                    placeholder="KMC-98412"
                    {...register("registration_number")}
                  />
                </div>
              </div>

              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Creating account...</span>
                  </>
                ) : (
                  <span>Create Account</span>
                )}
              </Button>
            </form>

            <p className="mt-5 text-center text-sm text-slate-600">
              Already registered?{" "}
              <Link to="/login" className="font-semibold text-primary hover:underline">
                Sign in
              </Link>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

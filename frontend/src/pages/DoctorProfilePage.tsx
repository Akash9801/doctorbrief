import { useEffect, useState } from "react";
import { Loader2, Save, Check } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { ApiError, authApi } from "@/services/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";

export function DoctorProfilePage() {
  const { doctor, setDoctor } = useAuth();
  const [form, setForm] = useState({
    full_name: doctor?.full_name || "",
    specialty: doctor?.specialty || "",
    clinic_name: doctor?.clinic_name || "",
    phone: doctor?.phone || "",
    registration_number: doctor?.registration_number || "",
  });
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (doctor) {
      setForm({
        full_name: doctor.full_name || "",
        specialty: doctor.specialty || "",
        clinic_name: doctor.clinic_name || "",
        phone: doctor.phone || "",
        registration_number: doctor.registration_number || "",
      });
    }
  }, [doctor]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSaved(false);
    setIsSaving(true);
    try {
      const updated = await authApi.updateProfile(form);
      setDoctor(updated);
      setSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to update profile.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Doctor Profile</h2>
        <p className="text-sm text-slate-500">
          Manage your clinical identity and clinic details displayed on approved notes.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Profile Details</CardTitle>
          <CardDescription>Signed in as {doctor?.email}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && <Alert variant="destructive">{error}</Alert>}
            {saved && (
              <Alert variant="success">Profile updated successfully.</Alert>
            )}

            <div className="space-y-1.5">
              <Label htmlFor="profile-name">Full Name</Label>
              <Input
                id="profile-name"
                value={form.full_name}
                onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
                required
              />
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="profile-specialty">Specialty</Label>
                <Input
                  id="profile-specialty"
                  value={form.specialty}
                  onChange={(e) => setForm((f) => ({ ...f, specialty: e.target.value }))}
                  placeholder="General Medicine"
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="profile-clinic">Clinic Name</Label>
                <Input
                  id="profile-clinic"
                  value={form.clinic_name}
                  onChange={(e) => setForm((f) => ({ ...f, clinic_name: e.target.value }))}
                  placeholder="Swasthya Care Clinic"
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="profile-phone">Phone</Label>
                <Input
                  id="profile-phone"
                  value={form.phone}
                  onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
                  placeholder="+91 9876543210"
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="profile-reg">Medical Registration No.</Label>
                <Input
                  id="profile-reg"
                  value={form.registration_number}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, registration_number: e.target.value }))
                  }
                  placeholder="KMC-98412"
                />
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <Button type="submit" disabled={isSaving}>
                {isSaving ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Saving...</span>
                  </>
                ) : saved ? (
                  <>
                    <Check className="h-4 w-4" />
                    <span>Saved</span>
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4" />
                    <span>Save Profile</span>
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

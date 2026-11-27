import { Menu, Plus } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";

interface HeaderProps {
  onMenuClick: () => void;
  title?: string;
}

export function Header({ onMenuClick, title }: HeaderProps) {
  const { doctor } = useAuth();

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200 bg-white/95 px-4 backdrop-blur-sm sm:px-6">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onMenuClick}
          className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden"
          aria-label="Open menu"
        >
          <Menu className="h-5 w-5" />
        </button>
        <h1 className="text-base font-semibold text-slate-900 sm:text-lg">
          {title || "DoctorBrief Workspace"}
        </h1>
      </div>

      <div className="flex items-center gap-3">
        <span className="hidden text-xs font-medium text-slate-500 md:inline">
          {doctor?.clinic_name || "Clinical Documentation Assistant"}
        </span>
        <Button asChild size="sm">
          <Link to="/consultations/new">
            <Plus className="h-4 w-4" />
            <span>New Consultation</span>
          </Link>
        </Button>
      </div>
    </header>
  );
}

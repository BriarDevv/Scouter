import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { Settings } from "lucide-react";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Configuración" description="Ajustes del sistema" />
      <EmptyState
        icon={Settings}
        title="Próximamente"
        description="La configuración del sistema estará disponible en una próxima versión."
      />
    </div>
  );
}

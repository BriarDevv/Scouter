"use client";

import { useState } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { LeadsTable } from "@/components/leads/leads-table";
import { Button } from "@/components/ui/button";
import { SkeletonTable } from "@/components/shared/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { getLeads, getExportUrl } from "@/lib/api/client";
import { usePageData } from "@/lib/hooks/use-page-data";
import type { Lead } from "@/types";
import { Plus, Users, RefreshCw, Download } from "lucide-react";

export default function LeadsPage() {
  const [exportOpen, setExportOpen] = useState(false);
  const { data: rawLeads, loading, error, refresh } = usePageData(
    async () => {
      const response = await getLeads({ page: 1, page_size: 200 });
      return response.items;
    },
  );
  const leads = rawLeads ?? [];

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8">
        <div className="space-y-6">
          <PageHeader
        title="Leads"
        description="Gestión de leads y pipeline comercial"
      >
        <div className="flex items-center gap-2">
          <div className="relative">
            <Button
              variant="outline"
              size="sm"
              className="rounded-xl gap-1.5"
              onClick={() => setExportOpen(!exportOpen)}
            >
              <Download className="h-3.5 w-3.5" />
              Exportar
            </Button>
            {exportOpen && (
              <div className="absolute right-0 top-full mt-1 z-50 w-44 rounded-xl border border-border bg-card shadow-lg py-1">
                {(["csv", "json", "xlsx"] as const).map((fmt) => (
                  <a
                    key={fmt}
                    href={getExportUrl(fmt)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block px-3 py-2 text-sm text-foreground hover:bg-muted transition-colors"
                    onClick={() => setExportOpen(false)}
                  >
                    Exportar {fmt.toUpperCase()}
                  </a>
                ))}
              </div>
            )}
          </div>
          <Tooltip>
            <TooltipTrigger
              render={
                <Button className="rounded-xl bg-violet-600 text-white hover:bg-violet-700 opacity-50 cursor-not-allowed" disabled />
              }
            >
              <Plus className="mr-2 h-4 w-4" />
              Nuevo Lead
            </TooltipTrigger>
            <TooltipContent>Próximamente</TooltipContent>
          </Tooltip>
        </div>
      </PageHeader>

      {error && (
        <div className="flex items-center gap-3 rounded-xl border border-rose-200 dark:border-rose-900/30 bg-rose-50 dark:bg-rose-950/20 px-4 py-3">
          <span className="text-sm text-rose-700 dark:text-rose-300">Error al cargar leads: {error.message}</span>
          <Button variant="outline" size="sm" className="rounded-xl gap-1.5" onClick={() => void refresh()}>
            <RefreshCw className="h-3.5 w-3.5" /> Reintentar
          </Button>
        </div>
      )}

      {loading ? (
        <SkeletonTable rows={10} />
      ) : leads.length === 0 ? (
        <EmptyState
          icon={Users}
          title="Sin leads"
          description="Todavía no hay leads en el sistema. Ejecutá un crawler para empezar a prospectar."
        />
      ) : (
        <LeadsTable leads={leads} />
      )}
        </div>
      </div>
    </div>
  );
}

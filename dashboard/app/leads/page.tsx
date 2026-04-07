"use client";

import { useEffect, useRef, useState } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { LeadsTable } from "@/components/leads/leads-table";
import { Button } from "@/components/ui/button";
import { SkeletonTable } from "@/components/shared/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { getExportUrl } from "@/lib/api/client";
import { useApi } from "@/lib/hooks/use-swr-fetch";
import type { Lead, PaginatedResponse } from "@/types";
import { Plus, Users, RefreshCw, Download, ChevronLeft, ChevronRight } from "lucide-react";

const PAGE_SIZE = 25;

export default function LeadsPage() {
  const [exportOpen, setExportOpen] = useState(false);
  const exportRef = useRef<HTMLDivElement>(null);
  const [currentPage, setCurrentPage] = useState(1);

  const { data: response, isLoading: loading, error, mutate } = useApi<PaginatedResponse<Lead>>(
    `/leads?page=${currentPage}&page_size=${PAGE_SIZE}`
  );

  const leads = response?.items ?? [];
  const total = response?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  useEffect(() => {
    if (!exportOpen) return;
    function handleClickOutside(e: MouseEvent) {
      if (exportRef.current && !exportRef.current.contains(e.target as Node)) {
        setExportOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [exportOpen]);

  function handleRefresh() {
    void mutate();
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8">
        <div className="space-y-6">
          <PageHeader
        title="Leads"
        description="Gestion de leads y pipeline comercial"
      >
        <div className="flex items-center gap-2">
          <div className="relative" ref={exportRef}>
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
            <TooltipContent>Proximamente</TooltipContent>
          </Tooltip>
        </div>
      </PageHeader>

      {error && (
        <div className="flex items-center gap-3 rounded-xl border border-rose-200 dark:border-rose-900/30 bg-rose-50 dark:bg-rose-950/20 px-4 py-3">
          <span className="text-sm text-rose-700 dark:text-rose-300">Error al cargar leads: {error instanceof Error ? error.message : "Error desconocido"}</span>
          <Button variant="outline" size="sm" className="rounded-xl gap-1.5" onClick={handleRefresh}>
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
          description="Todavia no hay leads en el sistema. Ejecuta un crawler para empezar a prospectar."
        />
      ) : (
        <>
          <LeadsTable leads={leads} />
          <div className="flex items-center justify-between border-t border-border pt-4">
            <span className="text-xs text-muted-foreground">
              {total} lead{total !== 1 ? "s" : ""} en total
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="rounded-xl gap-1.5"
                disabled={currentPage <= 1}
                onClick={() => setCurrentPage((p) => p - 1)}
              >
                <ChevronLeft className="h-3.5 w-3.5" />
                Anterior
              </Button>
              <span className="text-xs text-muted-foreground px-2">
                {currentPage} / {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                className="rounded-xl gap-1.5"
                disabled={currentPage >= totalPages}
                onClick={() => setCurrentPage((p) => p + 1)}
              >
                Siguiente
                <ChevronRight className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </>
      )}
        </div>
      </div>
    </div>
  );
}

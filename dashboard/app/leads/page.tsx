"use client";

import { useEffect, useRef, useState } from "react";
import { LeadsTable } from "@/components/leads/leads-table";
import { SkeletonTable } from "@/components/shared/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { getExportUrl } from "@/lib/api/client";
import { useApi } from "@/lib/hooks/use-swr-fetch";
import type { Lead, PaginatedResponse } from "@/types";
import { Users, Download, ChevronLeft, ChevronRight } from "lucide-react";

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

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8 space-y-5">

        {/* Header — minimal */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground font-heading">Leads</h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              <span className="font-data">{total}</span> leads en el sistema
            </p>
          </div>
          <div className="relative" ref={exportRef}>
            <button
              onClick={() => setExportOpen(!exportOpen)}
              className="flex items-center gap-1.5 rounded-xl border border-border px-3 py-2 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            >
              <Download className="h-3.5 w-3.5" />
              Exportar
            </button>
            {exportOpen && (
              <div className="absolute right-0 top-full mt-1 z-50 w-40 rounded-xl border border-border bg-card shadow-md py-1">
                {(["csv", "json", "xlsx"] as const).map((fmt) => (
                  <a
                    key={fmt}
                    href={getExportUrl(fmt)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block px-3 py-2 text-xs text-foreground hover:bg-muted transition-colors"
                    onClick={() => setExportOpen(false)}
                  >
                    {fmt.toUpperCase()}
                  </a>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-center gap-3 rounded-xl border border-red-200 dark:border-red-900/30 bg-red-50 dark:bg-red-950/20 px-4 py-3">
            <span className="text-xs text-red-700 dark:text-red-300">
              Error al cargar leads: {error instanceof Error ? error.message : "Error desconocido"}
            </span>
            <button
              onClick={() => void mutate()}
              className="rounded-lg border border-border px-2.5 py-1 text-xs text-muted-foreground hover:bg-muted transition-colors"
            >
              Reintentar
            </button>
          </div>
        )}

        {/* Content */}
        {loading ? (
          <SkeletonTable rows={10} />
        ) : leads.length === 0 ? (
          <EmptyState
            icon={Users}
            title="Sin leads"
            description="Ejecuta el pipeline desde el Panel para empezar a prospectar."
          />
        ) : (
          <>
            <LeadsTable leads={leads} />

            {/* Pagination */}
            <div className="flex items-center justify-between pt-2">
              <span className="text-[10px] text-muted-foreground">
                Pagina <span className="font-data">{currentPage}</span> de <span className="font-data">{totalPages}</span>
              </span>
              <div className="flex items-center gap-1">
                <button
                  disabled={currentPage <= 1}
                  onClick={() => setCurrentPage((p) => p - 1)}
                  className="flex items-center gap-1 rounded-lg border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground transition-colors disabled:opacity-30 disabled:pointer-events-none"
                >
                  <ChevronLeft className="h-3 w-3" />
                  Anterior
                </button>
                <button
                  disabled={currentPage >= totalPages}
                  onClick={() => setCurrentPage((p) => p + 1)}
                  className="flex items-center gap-1 rounded-lg border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground transition-colors disabled:opacity-30 disabled:pointer-events-none"
                >
                  Siguiente
                  <ChevronRight className="h-3 w-3" />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

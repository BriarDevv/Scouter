"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { getLeadResearch } from "@/lib/api/client";
import { useApi } from "@/lib/hooks/use-swr-fetch";
import type { Lead, LeadResearchReport, PaginatedResponse } from "@/types";
import Link from "next/link";
import { FileSearch, ExternalLink, CheckCircle, AlertCircle, Clock, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface DossierEntry {
  lead: Lead;
  research: LeadResearchReport;
}

const CONFIDENCE_COLORS: Record<string, string> = {
  confirmed: "text-emerald-600 dark:text-emerald-400",
  probable: "text-amber-600 dark:text-amber-400",
  unknown: "text-muted-foreground",
  mismatch: "text-red-600 dark:text-red-400",
};

const LEADS_PAGE_SIZE = 50;
const RESEARCH_CONCURRENCY = 5;

async function fetchResearchBatched(leads: Lead[]): Promise<DossierEntry[]> {
  const results: DossierEntry[] = [];
  for (let i = 0; i < leads.length; i += RESEARCH_CONCURRENCY) {
    const batch = leads.slice(i, i + RESEARCH_CONCURRENCY);
    const settled = await Promise.allSettled(
      batch.map(async (lead) => {
        const research = await getLeadResearch(lead.id);
        return research ? { lead, research } : null;
      })
    );
    for (const r of settled) {
      if (
        r.status === "fulfilled" &&
        r.value !== null &&
        r.value.research.status === "completed"
      ) {
        results.push(r.value);
      }
    }
  }
  return results;
}

export default function DossiersPage() {
  const [currentPage, setCurrentPage] = useState(1);
  const { data: leadsResponse, isLoading: leadsLoading } = useApi<PaginatedResponse<Lead>>(
    `/leads?page=${currentPage}&page_size=${LEADS_PAGE_SIZE}`
  );

  const [entries, setEntries] = useState<DossierEntry[]>([]);
  const [researchLoading, setResearchLoading] = useState(false);

  const total = leadsResponse?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / LEADS_PAGE_SIZE));
  const loading = leadsLoading || researchLoading;

  useEffect(() => {
    if (!leadsResponse) return;
    let active = true;

    async function loadResearch() {
      setResearchLoading(true);
      try {
        const highLeads = (leadsResponse!.items || []).filter(
          (l: Lead) => l.quality === "high" || (l.score != null && l.score >= 60)
        );
        const withDossiers = await fetchResearchBatched(highLeads);
        if (!active) return;
        setEntries(withDossiers);
      } catch (err) {
        console.warn("Failed to load dossiers:", err);
      }
      if (active) setResearchLoading(false);
    }

    void loadResearch();

    return () => {
      active = false;
    };
  }, [leadsResponse]);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8">
        <div className="space-y-6">
          <PageHeader
            title="Dossiers"
            description="Investigaciones completadas de leads HIGH"
          />
          <div className="space-y-2">
            {loading ? (
              <div className="text-muted-foreground text-sm py-8 text-center">
                Cargando dossiers...
              </div>
            ) : entries.length === 0 ? (
              <div className="text-muted-foreground text-sm py-8 text-center">
                No hay dossiers completados todavia. Ejecuta el pipeline para leads HIGH.
              </div>
            ) : (
              entries.map(({ lead, research }) => (
                <Link
                  key={lead.id}
                  href={`/leads/${lead.id}`}
                  className={cn(
                    "flex items-center gap-4 rounded-xl border border-border/60 p-4",
                    "hover:bg-muted/50 transition-colors"
                  )}
                >
                  <FileSearch className="h-5 w-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{lead.business_name}</div>
                    <div className="text-sm text-muted-foreground">
                      {lead.industry} · {lead.city}
                    </div>
                  </div>
                  <div className="flex items-center gap-3 text-xs">
                    {research.website_confidence && (
                      <span
                        className={cn(
                          "flex items-center gap-1",
                          CONFIDENCE_COLORS[research.website_confidence] || ""
                        )}
                      >
                        {research.website_confidence === "confirmed" ? (
                          <CheckCircle className="h-3 w-3" />
                        ) : research.website_confidence === "mismatch" ? (
                          <AlertCircle className="h-3 w-3" />
                        ) : (
                          <Clock className="h-3 w-3" />
                        )}
                        Web: {research.website_confidence}
                      </span>
                    )}
                    {research.detected_signals_json && (
                      <span className="text-muted-foreground">
                        {research.detected_signals_json.length} senales
                      </span>
                    )}
                    {research.research_duration_ms != null && (
                      <span className="text-muted-foreground">
                        {(research.research_duration_ms / 1000).toFixed(1)}s
                      </span>
                    )}
                  </div>
                  <ExternalLink className="h-4 w-4 text-muted-foreground shrink-0" />
                </Link>
              ))
            )}
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-border pt-4">
              <span className="text-xs text-muted-foreground">
                {total} lead{total !== 1 ? "s" : ""} · pagina {currentPage} / {totalPages}
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
          )}
        </div>
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { getLeads, getLeadResearch } from "@/lib/api/client";
import type { Lead, LeadResearchReport } from "@/types";
import Link from "next/link";
import { FileSearch, ExternalLink, CheckCircle, AlertCircle, Clock } from "lucide-react";
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

export default function DossiersPage() {
  const [entries, setEntries] = useState<DossierEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const res = await getLeads({ page_size: 200 });
        const highLeads = (res.items || []).filter(
          (l: Lead) => l.quality === "high" || (l.score != null && l.score >= 60)
        );

        // Fetch research for each HIGH lead in parallel
        const results = await Promise.allSettled(
          highLeads.map(async (lead) => {
            const research = await getLeadResearch(lead.id);
            return research ? { lead, research } : null;
          })
        );

        const withDossiers = results
          .filter(
            (r): r is PromiseFulfilledResult<DossierEntry | null> =>
              r.status === "fulfilled"
          )
          .map((r) => r.value)
          .filter(
            (entry): entry is DossierEntry =>
              entry !== null && entry.research.status === "completed"
          );

        setEntries(withDossiers);
      } catch {
        // ignore
      }
      setLoading(false);
    }
    load();
  }, []);

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
        </div>
      </div>
    </div>
  );
}

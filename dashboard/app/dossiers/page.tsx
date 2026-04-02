"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { LayoutShell } from "@/components/layout/layout-shell";
import { getLeads } from "@/lib/api/client";
import type { Lead } from "@/types";
import Link from "next/link";
import { FileSearch, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatRelativeTime, formatScore } from "@/lib/formatters";

export default function DossiersPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getLeads({ page_size: 200 })
      .then((res) => {
        const highLeads = (res.items || []).filter(
          (l: Lead) => l.quality === "high" || (l.score != null && l.score >= 60)
        );
        setLeads(highLeads);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <LayoutShell>
      <PageHeader
        title="Dossiers"
        description="Investigaciones y dossiers de leads HIGH"
      />
      <div className="space-y-2">
        {loading ? (
          <div className="text-muted-foreground text-sm py-8 text-center">
            Cargando...
          </div>
        ) : leads.length === 0 ? (
          <div className="text-muted-foreground text-sm py-8 text-center">
            No hay leads HIGH todavia
          </div>
        ) : (
          leads.map((lead) => (
            <Link
              key={lead.id}
              href={`/leads/${lead.id}`}
              className={cn(
                "flex items-center gap-4 rounded-xl border border-border/60 p-4",
                "hover:bg-muted/50 transition-colors"
              )}
            >
              <FileSearch className="h-5 w-5 text-muted-foreground shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="font-medium truncate">{lead.business_name}</div>
                <div className="text-sm text-muted-foreground">
                  {lead.industry} · {lead.city}
                </div>
              </div>
              <div className="text-sm font-medium">
                Score: {formatScore(lead.score)}
              </div>
              <div className="text-xs text-muted-foreground">
                {formatRelativeTime(lead.created_at)}
              </div>
              <ExternalLink className="h-4 w-4 text-muted-foreground shrink-0" />
            </Link>
          ))
        )}
      </div>
    </LayoutShell>
  );
}

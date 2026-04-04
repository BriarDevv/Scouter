"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { listBriefs } from "@/lib/api/client";
import type { CommercialBrief } from "@/types";
import Link from "next/link";
import { Briefcase, ExternalLink, Phone, PhoneOff } from "lucide-react";
import { cn } from "@/lib/utils";

const TIER_COLORS: Record<string, string> = {
  low: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
  medium: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  high: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
  premium: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
};

const PRIORITY_COLORS: Record<string, string> = {
  immediate: "text-red-600 dark:text-red-400",
  high: "text-amber-600 dark:text-amber-400",
  normal: "text-foreground",
  low: "text-muted-foreground",
};

export default function BriefsPage() {
  const [briefs, setBriefs] = useState<CommercialBrief[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listBriefs({ limit: 100 })
      .then(setBriefs)
      .catch((err) => console.warn("Failed to load briefs:", err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8">
        <div className="space-y-6">
          <PageHeader
            title="Commercial Briefs"
            description="Evaluaciones comerciales de leads HIGH"
          />
          <div className="space-y-2">
            {loading ? (
              <div className="text-muted-foreground text-sm py-8 text-center">
                Cargando...
              </div>
            ) : briefs.length === 0 ? (
              <div className="text-muted-foreground text-sm py-8 text-center">
                No hay briefs generados todavia
              </div>
            ) : (
              briefs.map((brief) => (
                <Link
                  key={brief.id}
                  href={`/leads/${brief.lead_id}`}
                  className={cn(
                    "flex items-center gap-4 rounded-xl border border-border/60 p-4",
                    "hover:bg-muted/50 transition-colors"
                  )}
                >
                  <Briefcase className="h-5 w-5 text-muted-foreground shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">
                        Opp: {brief.opportunity_score?.toFixed(0) ?? "\u2014"}
                      </span>
                      {brief.budget_tier && (
                        <span
                          className={cn(
                            "rounded-md px-1.5 py-0.5 text-[10px] font-medium",
                            TIER_COLORS[brief.budget_tier] || ""
                          )}
                        >
                          {brief.budget_tier.toUpperCase()}
                        </span>
                      )}
                      {brief.estimated_scope && (
                        <span className="text-xs text-muted-foreground">
                          {brief.estimated_scope.replace(/_/g, " ")}
                        </span>
                      )}
                    </div>
                    <div className="text-sm text-muted-foreground truncate">
                      {brief.why_this_lead_matters || "Sin descripcion"}
                    </div>
                  </div>
                  {brief.estimated_budget_min != null &&
                    brief.estimated_budget_max != null && (
                      <div className="text-sm font-mono">
                        USD {brief.estimated_budget_min}\u2013
                        {brief.estimated_budget_max}
                      </div>
                    )}
                  <div className="flex items-center gap-1">
                    {brief.should_call === "yes" ? (
                      <Phone className="h-4 w-4 text-green-600 dark:text-green-400" />
                    ) : brief.should_call === "maybe" ? (
                      <Phone className="h-4 w-4 text-amber-500" />
                    ) : (
                      <PhoneOff className="h-4 w-4 text-muted-foreground" />
                    )}
                  </div>
                  {brief.contact_priority && (
                    <span
                      className={cn(
                        "text-xs font-medium",
                        PRIORITY_COLORS[brief.contact_priority] || ""
                      )}
                    >
                      {brief.contact_priority}
                    </span>
                  )}
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

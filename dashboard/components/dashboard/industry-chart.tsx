"use client";

import { cn } from "@/lib/utils";
import type { IndustryBreakdown } from "@/types";

export function IndustryChart({ data }: { data: IndustryBreakdown[] }) {
  const sorted = [...data].sort((a, b) => b.count - a.count).slice(0, 8);
  const maxCount = sorted[0]?.count || 1;

  return (
    <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
      <div className="flex items-baseline justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground font-heading">Top Industrias</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">Leads por rubro</p>
        </div>
        <span className="text-xs text-muted-foreground font-data">{sorted.length} rubros</span>
      </div>

      {sorted.length === 0 ? (
        <p className="mt-6 text-center text-xs text-muted-foreground py-8">Sin datos de industrias</p>
      ) : (
        <div className="mt-5 space-y-px">
          {sorted.map((industry, i) => {
            const pct = (industry.count / maxCount) * 100;

            return (
              <div
                key={industry.industry}
                className="group relative flex items-center gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-muted/50"
              >
                <div className="absolute inset-0 rounded-lg overflow-hidden">
                  <div
                    className="h-full bg-foreground/[0.06] transition-[width] duration-700"
                    style={{ width: `${pct}%` }}
                  />
                </div>

                <span className="relative text-[10px] text-muted-foreground/50 font-data w-4 text-right">{i + 1}</span>
                <span className="relative flex-1 text-xs text-foreground font-medium truncate">{industry.industry}</span>
                <span className={cn(
                  "relative text-[10px] font-data font-bold px-1.5 py-0.5 rounded-full",
                  industry.avg_score >= 60 ? "bg-emerald-100 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300"
                    : industry.avg_score >= 30 ? "bg-amber-100 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300"
                    : "bg-red-100 dark:bg-red-950/40 text-red-700 dark:text-red-300"
                )}>
                  score {industry.avg_score.toFixed(0)}
                </span>
                <span className="relative font-data text-sm font-bold text-foreground tabular-nums w-8 text-right">
                  {industry.count}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

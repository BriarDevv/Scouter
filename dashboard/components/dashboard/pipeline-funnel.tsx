"use client";

import type { PipelineStage } from "@/types";
import { formatPercent } from "@/lib/formatters";

export function PipelineFunnel({ stages }: { stages: PipelineStage[] }) {
  const maxCount = stages[0]?.count || 1;

  return (
    <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
      <h3 className="text-sm font-semibold text-foreground font-heading">Pipeline Comercial</h3>
      <p className="mt-0.5 text-xs text-muted-foreground">Embudo de conversión por etapa</p>

      <div className="mt-5 space-y-2">
        {stages.map((stage, i) => {
          const widthPercent = Math.max((stage.count / maxCount) * 100, 8);
          const conversionFromPrev = i > 0
            ? ((stage.count / stages[i - 1].count) * 100).toFixed(0) + "%"
            : null;

          return (
            <div key={stage.stage} className="group flex items-center gap-3">
              <div className="w-24 text-right">
                <span className="text-xs font-medium text-muted-foreground font-heading">{stage.label}</span>
              </div>
              <div className="flex-1">
                <div className="relative h-8 w-full overflow-hidden rounded-lg bg-muted">
                  <div
                    className="absolute inset-y-0 left-0 flex items-center rounded-lg px-3 transition-all duration-500"
                    style={{ width: `${widthPercent}%`, backgroundColor: stage.color }}
                  >
                    <span className="text-xs font-semibold text-white drop-shadow-sm font-data">
                      {stage.count}
                    </span>
                  </div>
                </div>
              </div>
              <div className="w-14 text-right">
                {conversionFromPrev ? (
                  <span className="text-xs text-muted-foreground font-data">{conversionFromPrev}</span>
                ) : (
                  <span className="text-xs text-muted-foreground/50">—</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

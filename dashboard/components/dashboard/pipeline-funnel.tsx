"use client";

import { cn } from "@/lib/utils";
import type { PipelineStage } from "@/types";

export function PipelineFunnel({ stages }: { stages: PipelineStage[] }) {
  const maxCount = stages[0]?.count || 1;
  const isEmpty = stages.every((s) => s.count === 0);

  return (
    <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
      <div className="flex items-baseline justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground font-heading">Pipeline</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">Embudo de conversion</p>
        </div>
        {!isEmpty && (
          <span className="text-2xl font-bold text-foreground font-data">{maxCount}</span>
        )}
      </div>

      {isEmpty ? (
        <p className="mt-6 text-center text-xs text-muted-foreground py-8">Sin leads en el pipeline</p>
      ) : (
        <div className="mt-5 space-y-px">
          {stages.map((stage, i) => {
            const pct = (stage.count / maxCount) * 100;
            const drop = i > 0 && stages[i - 1].count > 0
              ? ((stage.count / stages[i - 1].count) * 100).toFixed(0)
              : null;

            return (
              <div
                key={stage.stage}
                className={cn(
                  "group relative flex items-center gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-muted/50",
                  stage.count === 0 && "opacity-40"
                )}
              >
                <div className="absolute inset-0 rounded-lg overflow-hidden">
                  <div
                    className="h-full bg-foreground/[0.04] transition-[width] duration-700"
                    style={{ width: `${pct}%` }}
                  />
                </div>

                <span className="relative w-28 text-xs text-muted-foreground truncate">{stage.label}</span>
                <span className="relative font-data text-sm font-bold text-foreground ml-auto tabular-nums">
                  {stage.count}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

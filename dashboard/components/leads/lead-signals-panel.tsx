"use client";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/shared/empty-state";
import { SIGNAL_CONFIG } from "@/lib/constants";
import { RefreshCw, Sparkles, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { LeadSignal } from "@/types";

interface LeadSignalsPanelProps {
  signals: LeadSignal[];
  isRunningPipeline: boolean;
  onRunPipeline: () => void;
}

export function LeadSignalsPanel({ signals, isRunningPipeline, onRunPipeline }: LeadSignalsPanelProps) {
  return (
    <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
      <h3 className="text-sm font-semibold text-foreground mb-3 font-heading">Señales Detectadas</h3>
      <div className="space-y-2">
        {signals.map((s) => {
          const config = SIGNAL_CONFIG[s.signal_type];
          return (
            <div
              key={s.id}
              className={cn(
                "flex items-center gap-3 rounded-xl px-3 py-2 text-sm",
                config?.severity === "positive"
                  ? "bg-emerald-50/60 dark:bg-emerald-950/20"
                  : "bg-muted"
              )}
            >
              <span className="text-base">{config?.emoji || "?"}</span>
              <div>
                <span className="font-medium text-foreground/80">{config?.label || s.signal_type}</span>
                {s.detail && <span className="text-muted-foreground"> — {s.detail}</span>}
              </div>
            </div>
          );
        })}
        {signals.length === 0 && (
          <EmptyState
            icon={Sparkles}
            title="Sin señales detectadas"
            description="Ejecutá el pipeline para detectar señales."
            className="py-6"
          >
            <Button
              variant="outline"
              size="sm"
              className="rounded-xl gap-1.5"
              onClick={onRunPipeline}
              disabled={isRunningPipeline}
            >
              {isRunningPipeline ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
              Ejecutar Pipeline
            </Button>
          </EmptyState>
        )}
      </div>
    </div>
  );
}

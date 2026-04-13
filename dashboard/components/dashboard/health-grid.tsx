"use client";

import { RefreshCw, Database, HardDrive, Brain, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import type { HealthComponent } from "@/types";

const HEALTH_META: Record<string, { label: string; icon: React.ElementType; desc: string }> = {
  database: { label: "BD", icon: Database, desc: "PostgreSQL" },
  redis: { label: "Redis", icon: HardDrive, desc: "Cache & broker" },
  ollama: { label: "Ollama", icon: Brain, desc: "Modelos IA" },
  celery: { label: "Celery", icon: Zap, desc: "Workers async" },
};

interface HealthGridProps {
  health: HealthComponent[];
  healthLoading: boolean;
  onRefresh: () => void;
}

export function HealthGrid({ health, healthLoading, onRefresh }: HealthGridProps) {
  const items = health.length > 0
    ? health.map((c) => ({ ...c, meta: HEALTH_META[c.name] }))
    : Object.entries(HEALTH_META).map(([name, meta]) => ({ name, status: "pending" as const, latency_ms: null, error: null, meta }));

  return (
    <div className="flex flex-col gap-2 flex-1">
      <div className="flex items-center justify-between">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Sistema</p>
        <button
          onClick={onRefresh}
          className="rounded-lg p-1 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          title="Actualizar estado"
        >
          <RefreshCw className={cn("h-3 w-3", healthLoading && "animate-spin")} />
        </button>
      </div>
      <div className="grid grid-cols-2 gap-1.5 flex-1">
        {items.map((c) => {
          const Icon = c.meta?.icon ?? Brain;
          const isPending = c.status === "pending";
          return (
            <div
              key={c.name}
              className={cn(
                "flex items-center gap-2.5 rounded-lg border px-3 py-2.5 transition-colors",
                isPending
                  ? "border-border/40 bg-muted/20"
                  : c.status === "ok"
                  ? "border-emerald-200 dark:border-emerald-900/30 bg-emerald-50/50 dark:bg-emerald-950/10"
                  : c.status === "degraded"
                  ? "border-amber-200 dark:border-amber-900/30 bg-amber-50/50 dark:bg-amber-950/10"
                  : "border-red-200 dark:border-red-900/30 bg-red-50/50 dark:bg-red-950/10"
              )}
              title={c.error || (c.latency_ms ? `${c.latency_ms.toFixed(0)}ms` : "")}
            >
              <Icon className={cn("h-4 w-4 shrink-0", isPending ? "text-muted-foreground/30" : "text-muted-foreground")} />
              <div className="flex-1 min-w-0">
                <p className={cn("text-xs font-semibold", isPending ? "text-muted-foreground/40" : "text-foreground")}>
                  {c.meta?.label ?? c.name}
                </p>
                <p className="text-[10px] text-muted-foreground truncate">
                  {isPending ? c.meta?.desc : c.latency_ms != null
                    ? `${c.meta?.desc} · ${c.latency_ms < 1000 ? `${c.latency_ms.toFixed(0)}ms` : `${(c.latency_ms / 1000).toFixed(1)}s`}`
                    : c.meta?.desc}
                </p>
              </div>
              {!isPending && (
                <span className={cn(
                  "h-2 w-2 rounded-full shrink-0",
                  c.status === "ok" ? "bg-emerald-500" : c.status === "degraded" ? "bg-amber-500" : "bg-red-500"
                )} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

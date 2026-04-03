"use client";

import { Power, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import type { HealthComponent } from "@/types";

const HEALTH_DOT: Record<string, string> = {
  ok: "bg-emerald-500",
  degraded: "bg-amber-500",
  error: "bg-red-500",
};

const HEALTH_LABEL: Record<string, string> = {
  database: "BD",
  redis: "Redis",
  ollama: "Ollama",
  celery: "Celery",
};

interface HealthStatusProps {
  health: HealthComponent[];
  healthLoading?: boolean;
  onRefresh?: () => void;
}

export function HealthStatus({ health, healthLoading, onRefresh }: HealthStatusProps) {
  const allOk = health.length > 0 && health.every((c) => c.status === "ok");

  return (
    <div className="flex items-center justify-between border-b border-border px-5 py-3">
      <div className="flex items-center gap-3">
        <div className={cn(
          "flex h-8 w-8 items-center justify-center rounded-lg",
          allOk ? "bg-emerald-50 dark:bg-emerald-950/40" : "bg-amber-50 dark:bg-amber-950/40"
        )}>
          <Power className={cn("h-4 w-4", allOk ? "text-emerald-600 dark:text-emerald-400" : "text-amber-600 dark:text-amber-400")} />
        </div>
        <div>
          <h3 className="text-sm font-bold text-foreground">Centro de Control</h3>
          <p className="text-[11px] text-muted-foreground">
            {allOk ? "Todos los servicios operativos" : "Algunos servicios con problemas"}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Health dots inline */}
        <div className="hidden sm:flex items-center gap-2">
          {health.map((comp) => (
            <div
              key={comp.name}
              className="flex items-center gap-1.5"
              title={comp.error || `${HEALTH_LABEL[comp.name] ?? comp.name}: ${comp.latency_ms?.toFixed(0) ?? "?"}ms`}
            >
              <span className={cn("h-2 w-2 rounded-full", HEALTH_DOT[comp.status] ?? "bg-slate-400 animate-pulse")} />
              <span className="text-[11px] text-muted-foreground">{HEALTH_LABEL[comp.name] ?? comp.name}</span>
            </div>
          ))}
        </div>

        <button
          onClick={onRefresh}
          className="rounded-lg p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          title="Actualizar estado"
        >
          <RefreshCw className={cn("h-4 w-4", healthLoading && "animate-spin")} />
        </button>
      </div>
    </div>
  );
}

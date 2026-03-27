"use client";

import { Database, Server, Brain, Cog } from "lucide-react";
import { cn } from "@/lib/utils";
import type { HealthComponent, SystemHealth } from "@/types";

const COMPONENT_META: Record<string, { label: string; icon: typeof Database }> = {
  database: { label: "Base de datos", icon: Database },
  redis:    { label: "Redis",         icon: Server },
  ollama:   { label: "Ollama",        icon: Brain },
  celery:   { label: "Celery",        icon: Cog },
};

const STATUS_DOT: Record<string, string> = {
  ok:       "bg-emerald-500",
  degraded: "bg-amber-500",
  error:    "bg-red-500",
  checking: "bg-slate-400 animate-pulse",
};

const STATUS_LABEL: Record<string, string> = {
  ok:       "Operativo",
  degraded: "Degradado",
  error:    "Error",
  checking: "Verificando...",
};

function ComponentDot({ component }: { component: HealthComponent }) {
  const meta = COMPONENT_META[component.name];
  if (!meta) return null;
  const Icon = meta.icon;

  return (
    <div
      className="group relative flex items-center gap-2 px-3 py-2 rounded-xl transition hover:bg-muted/50"
      title={component.error || undefined}
    >
      <span
        className={cn("h-2.5 w-2.5 rounded-full", STATUS_DOT[component.status])}
      />
      <Icon className="h-3.5 w-3.5 text-muted-foreground" />
      <span className="text-xs font-medium text-muted-foreground">{meta.label}</span>
      {component.latency_ms !== null && (
        <span className="hidden text-[11px] text-muted-foreground/60 group-hover:inline">
          {component.latency_ms.toFixed(0)}ms
        </span>
      )}
    </div>
  );
}

interface SystemHealthStripProps {
  health?: SystemHealth | null;
  loading?: boolean;
  error?: string | null;
}

export function SystemHealthStrip({ health, loading = false, error }: SystemHealthStripProps) {
  const overallStatus = health?.status ?? "checking";

  return (
    <div className="rounded-2xl border border-border bg-card px-4 py-2.5 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1">
          <span
            className={cn("h-2 w-2 rounded-full", STATUS_DOT[overallStatus])}
          />
          <span className="text-sm font-heading font-medium text-foreground">
            {STATUS_LABEL[overallStatus]}
          </span>
          {error && (
            <span className="text-xs text-muted-foreground">&middot; {error}</span>
          )}
        </div>

        <div className="flex items-center gap-1">
          {loading && !health ? (
            <div className="flex items-center gap-2 px-3 py-2">
              <span className="h-3.5 w-3.5 rounded-full bg-muted animate-pulse" />
              <span className="text-xs text-muted-foreground">Verificando componentes...</span>
            </div>
          ) : health ? (
            health.components.map((component) => (
              <ComponentDot key={component.name} component={component} />
            ))
          ) : null}
        </div>
      </div>
    </div>
  );
}

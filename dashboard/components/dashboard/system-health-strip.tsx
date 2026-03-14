"use client";

import { useEffect, useState } from "react";
import { Database, Server, Brain, Cog, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { getSystemHealth } from "@/lib/api/client";
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

export function SystemHealthStrip() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function fetchHealth() {
    try {
      const data = await getSystemHealth();
      setHealth(data);
      setError(null);
    } catch (err) {
      console.warn("No se pudo obtener el estado del sistema", err);
      setError("Sin conexión al backend");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void fetchHealth();
    const interval = setInterval(() => void fetchHealth(), 30_000);
    return () => clearInterval(interval);
  }, []);

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
            <span className="text-xs text-muted-foreground">· {error}</span>
          )}
        </div>

        <div className="flex items-center gap-1">
          {loading || !health ? (
            <div className="flex items-center gap-2 px-3 py-2">
              <RefreshCw className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Verificando componentes...</span>
            </div>
          ) : (
            health.components.map((component) => (
              <ComponentDot key={component.name} component={component} />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

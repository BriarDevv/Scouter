"use client";

import { useEffect, useState } from "react";
import { Brain, CheckCircle, AlertTriangle, Clock } from "lucide-react";
import { apiFetch } from "@/lib/api/client";

interface AiHealthData {
  approval_rate: number | null;
  fallback_rate: number | null;
  avg_latency_ms: number | null;
  invocations_24h: number;
}

export function AiHealthCard() {
  const [data, setData] = useState<AiHealthData | null>(null);

  useEffect(() => {
    // For now, this is a placeholder that will work once the backend endpoint exists
    // GET /api/v1/performance/ai-health
    async function load() {
      try {
        setData(await apiFetch<AiHealthData>("/performance/ai-health"));
      } catch {
        // Endpoint may not be running — show placeholder
      }
    }
    load();
  }, []);

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-center gap-2 mb-3">
        <Brain className="h-4 w-4 text-violet-600 dark:text-violet-400" />
        <h3 className="text-sm font-medium">Salud IA</h3>
      </div>

      {data ? (
        <div className="grid grid-cols-2 gap-3">
          <Metric
            icon={CheckCircle}
            label="Aprobacion"
            value={data.approval_rate != null ? `${Math.round(data.approval_rate * 100)}%` : "—"}
            color={data.approval_rate != null && data.approval_rate >= 0.7 ? "emerald" : "amber"}
          />
          <Metric
            icon={AlertTriangle}
            label="Fallbacks"
            value={data.fallback_rate != null ? `${Math.round(data.fallback_rate * 100)}%` : "—"}
            color={data.fallback_rate != null && data.fallback_rate <= 0.1 ? "emerald" : "red"}
          />
          <Metric
            icon={Clock}
            label="Latencia prom."
            value={data.avg_latency_ms != null ? `${Math.round(data.avg_latency_ms)}ms` : "—"}
            color="blue"
          />
          <Metric
            icon={Brain}
            label="Invocaciones 24h"
            value={String(data.invocations_24h)}
            color="violet"
          />
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          <Metric icon={CheckCircle} label="Aprobacion" value="—" color="muted" />
          <Metric icon={AlertTriangle} label="Fallbacks" value="—" color="muted" />
          <Metric icon={Clock} label="Latencia prom." value="—" color="muted" />
          <Metric icon={Brain} label="Invocaciones 24h" value="—" color="muted" />
        </div>
      )}
    </div>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  color: string;
}) {
  const textColor = color === "muted"
    ? "text-muted-foreground"
    : `text-${color}-600 dark:text-${color}-400`;

  return (
    <div className="text-center">
      <Icon className={`h-4 w-4 mx-auto mb-1 ${textColor}`} />
      <p className={`text-lg font-semibold ${textColor}`}>{value}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

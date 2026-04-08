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
    async function load() {
      try {
        setData(await apiFetch<AiHealthData>("/performance/ai-health"));
      } catch (err) {
        console.error("ai_health_fetch_failed", err);
      }
    }
    load();
  }, []);

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-center gap-2 mb-3">
        <Brain className="h-4 w-4 text-foreground dark:text-foreground" />
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

const METRIC_COLOR_CLASSES: Record<string, string> = {
  emerald: "text-emerald-600 dark:text-emerald-400",
  red:     "text-red-600 dark:text-red-400",
  amber:   "text-amber-600 dark:text-amber-400",
  blue:    "text-blue-600 dark:text-blue-400",
  violet:  "text-foreground dark:text-foreground",
  muted:   "text-muted-foreground",
};

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
  const textColor = METRIC_COLOR_CLASSES[color] ?? "text-muted-foreground";

  return (
    <div className="text-center">
      <Icon className={`h-4 w-4 mx-auto mb-1 ${textColor}`} />
      <p className={`text-lg font-semibold ${textColor}`}>{value}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

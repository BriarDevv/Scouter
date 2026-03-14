"use client";

import { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { TerritoryWithStats } from "@/types";

interface TerritoryComparisonProps {
  territories: TerritoryWithStats[];
  metric: "lead_count" | "avg_score" | "conversion_rate" | "qualified_count";
}

const METRIC_LABELS: Record<string, { label: string; format: (v: number) => string }> = {
  lead_count: { label: "Leads", format: (v) => String(v) },
  avg_score: { label: "Score promedio", format: (v) => v.toFixed(1) },
  conversion_rate: { label: "Tasa de conversion", format: (v) => `${(v * 100).toFixed(1)}%` },
  qualified_count: { label: "Calificados", format: (v) => String(v) },
};

export function TerritoryComparison({ territories, metric }: TerritoryComparisonProps) {
  const data = useMemo(
    () =>
      territories
        .filter((t) => t.is_active)
        .map((t) => ({
          name: t.name,
          value: t[metric],
          color: t.color,
        }))
        .sort((a, b) => b.value - a.value),
    [territories, metric]
  );

  const metricInfo = METRIC_LABELS[metric] ?? METRIC_LABELS.lead_count;

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
        No hay territorios activos para comparar.
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
      <h3 className="mb-4 text-sm font-semibold font-heading text-foreground">
        Comparacion de territorios — {metricInfo.label}
      </h3>
      <ResponsiveContainer width="100%" height={Math.max(200, data.length * 40)}>
        <BarChart data={data} layout="vertical" margin={{ left: 10, right: 20, top: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
          <XAxis type="number" className="text-xs fill-muted-foreground" />
          <YAxis
            type="category"
            dataKey="name"
            width={120}
            className="text-xs fill-muted-foreground font-heading"
            tick={{ fontSize: 12 }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "var(--color-card)",
              borderColor: "var(--color-border)",
              borderRadius: "0.75rem",
              fontSize: "0.75rem",
            }}
            formatter={(value) => [metricInfo.format(Number(value)), metricInfo.label]}
          />
          <Bar dataKey="value" radius={[0, 6, 6, 0]} maxBarSize={28}>
            {data.map((entry, index) => (
              <Cell key={index} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

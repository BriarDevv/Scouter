"use client";

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from "recharts";
import { formatPercent } from "@/lib/formatters";
import { CHART_TOOLTIP_STYLE } from "@/lib/constants";
import type { IndustryBreakdown } from "@/types";

const CONVERSION_COLORS = ["oklch(0.25 0 0)", "oklch(0.40 0 0)", "oklch(0.55 0 0)", "oklch(0.70 0 0)", "oklch(0.85 0 0)"];

export function IndustryConversionChart({ data }: { data: IndustryBreakdown[] }) {
  const sorted = [...data].sort((a, b) => b.conversion_rate - a.conversion_rate);

  return (
    <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
      <h3 className="text-sm font-semibold text-foreground mb-4 font-heading">Conversión por Rubro</h3>
      <div className="h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={sorted} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} tickLine={false} axisLine={false} />
            <YAxis type="category" dataKey="industry" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={false} width={90} />
            <Tooltip formatter={(v) => formatPercent(Number(v))} contentStyle={CHART_TOOLTIP_STYLE} />
            <Bar dataKey="conversion_rate" radius={[0, 6, 6, 0]} barSize={18}>
              {sorted.map((_, i) => (
                <Cell key={i} fill={CONVERSION_COLORS[i % CONVERSION_COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { IndustryBreakdown } from "@/types";

export function IndustryChart({ data }: { data: IndustryBreakdown[] }) {
  const sorted = [...data].sort((a, b) => b.count - a.count).slice(0, 8);

  return (
    <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-900 font-heading">Top Industrias</h3>
      <p className="mt-0.5 text-xs text-slate-500">Leads por rubro</p>

      <div className="mt-4 h-[250px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={sorted} layout="vertical" margin={{ top: 0, right: 4, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 11, fill: "#94a3b8" }} tickLine={false} axisLine={false} />
            <YAxis
              type="category"
              dataKey="industry"
              tick={{ fontSize: 11, fill: "#64748b" }}
              tickLine={false}
              axisLine={false}
              width={90}
            />
            <Tooltip
              contentStyle={{
                background: "white",
                border: "1px solid #e2e8f0",
                borderRadius: "12px",
                boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.05)",
                fontSize: 12,
              }}
              formatter={(value, name) => {
                if (name === "count") return [String(value), "Leads"];
                return [String(value), String(name)];
              }}
            />
            <Bar dataKey="count" fill="#8b5cf6" radius={[0, 6, 6, 0]} barSize={20} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

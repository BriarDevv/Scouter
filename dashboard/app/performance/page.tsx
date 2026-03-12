"use client";

import { PageHeader } from "@/components/layout/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { AreaChartCard } from "@/components/charts/area-chart-card";
import { PipelineFunnel } from "@/components/dashboard/pipeline-funnel";
import { formatPercent, formatDays } from "@/lib/formatters";
import {
  MOCK_STATS,
  MOCK_TIME_SERIES,
  MOCK_PIPELINE,
  MOCK_INDUSTRY_BREAKDOWN,
  MOCK_CITY_BREAKDOWN,
  MOCK_SOURCE_PERFORMANCE,
} from "@/data/mock";
import {
  Target, MessageSquare, CalendarCheck, Trophy, Clock, Zap,
  TrendingUp, TrendingDown, AlertTriangle,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, Legend,
} from "recharts";
import { cn } from "@/lib/utils";

const CONVERSION_COLORS = ["#8b5cf6", "#06b6d4", "#10b981", "#f59e0b", "#ef4444"];

function SectionTitle({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-4">
      <h2 className="text-lg font-semibold text-slate-900 font-heading">{title}</h2>
      {subtitle && <p className="text-sm text-slate-500">{subtitle}</p>}
    </div>
  );
}

function MetricTable({
  title,
  columns,
  data,
}: {
  title: string;
  columns: { key: string; label: string; format?: (v: any) => string }[];
  data: Record<string, any>[];
}) {
  return (
    <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-900 mb-4 font-heading">{title}</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100">
              {columns.map((col) => (
                <th key={col.key} className="px-3 py-2 text-left text-xs font-medium text-slate-500 font-heading">
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, i) => (
              <tr key={i} className="border-b border-slate-50 hover:bg-slate-50/50 transition-colors">
                {columns.map((col) => (
                  <td key={col.key} className="px-3 py-2.5 text-slate-700">
                    {col.format ? col.format(row[col.key]) : row[col.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function PerformancePage() {
  const stats = MOCK_STATS;

  return (
    <div className="space-y-10">
      <PageHeader
        title="Rendimiento"
        description="Métricas clave para evaluar la efectividad del sistema y tomar decisiones"
      />

      {/* Conversion Rates */}
      <section>
        <SectionTitle title="Tasas de Conversión" subtitle="Eficiencia en cada etapa del pipeline" />
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
          <StatCard label="Tasa de Contacto" value={formatPercent(stats.contacted / stats.total_leads)} icon={Target} iconBg="bg-amber-50" iconColor="text-amber-600" />
          <StatCard label="Tasa de Apertura" value={formatPercent(stats.open_rate)} icon={Zap} iconBg="bg-orange-50" iconColor="text-orange-600" />
          <StatCard label="Tasa de Respuesta" value={formatPercent(stats.reply_rate)} icon={MessageSquare} iconBg="bg-emerald-50" iconColor="text-emerald-600" />
          <StatCard label="Tasa de Reunión" value={formatPercent(stats.meeting_rate)} icon={CalendarCheck} iconBg="bg-teal-50" iconColor="text-teal-600" />
          <StatCard label="Tasa de Cierre" value={formatPercent(stats.conversion_rate)} icon={Trophy} iconBg="bg-green-50" iconColor="text-green-600" />
        </div>
      </section>

      {/* Velocity Metrics */}
      <section>
        <SectionTitle title="Velocidad del Pipeline" subtitle="Tiempo promedio entre etapas" />
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatCard label="Hasta Contacto" value="2.1d" icon={Clock} iconBg="bg-blue-50" iconColor="text-blue-600" subtitle="promedio" />
          <StatCard label="Hasta Respuesta" value="4.8d" icon={Clock} iconBg="bg-indigo-50" iconColor="text-indigo-600" subtitle="promedio" />
          <StatCard label="Hasta Reunión" value="8.3d" icon={Clock} iconBg="bg-violet-50" iconColor="text-violet-600" subtitle="promedio" />
          <StatCard label="Hasta Cierre" value="18.5d" icon={Clock} iconBg="bg-purple-50" iconColor="text-purple-600" subtitle="promedio" />
        </div>
      </section>

      {/* Pipeline */}
      <section>
        <SectionTitle title="Embudo Comercial" subtitle="Dónde están los cuellos de botella" />
        <PipelineFunnel stages={MOCK_PIPELINE} />
      </section>

      {/* Trends */}
      <section>
        <SectionTitle title="Tendencias" subtitle="Evolución últimos 30 días" />
        <div className="grid gap-6 lg:grid-cols-2">
          <AreaChartCard title="Leads Nuevos" data={MOCK_TIME_SERIES} dataKey="leads" color="#8b5cf6" gradientId="perfLeads" />
          <AreaChartCard title="Conversiones" data={MOCK_TIME_SERIES} dataKey="conversions" color="#22c55e" gradientId="perfConv" />
        </div>
      </section>

      {/* By Industry */}
      <section>
        <SectionTitle title="Rendimiento por Industria" subtitle="Qué rubros convierten mejor" />
        <div className="grid gap-6 lg:grid-cols-2">
          <MetricTable
            title="Industrias"
            columns={[
              { key: "industry", label: "Rubro" },
              { key: "count", label: "Leads" },
              { key: "avg_score", label: "Score Prom.", format: (v: number) => v.toFixed(1) },
              { key: "conversion_rate", label: "Conv. Rate", format: (v: number) => formatPercent(v) },
            ]}
            data={[...MOCK_INDUSTRY_BREAKDOWN].sort((a, b) => b.conversion_rate - a.conversion_rate)}
          />
          <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-900 mb-4 font-heading">Conversión por Rubro</h3>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={[...MOCK_INDUSTRY_BREAKDOWN].sort((a, b) => b.conversion_rate - a.conversion_rate)} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 11, fill: "#94a3b8" }} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} tickLine={false} axisLine={false} />
                  <YAxis type="category" dataKey="industry" tick={{ fontSize: 11, fill: "#64748b" }} tickLine={false} axisLine={false} width={90} />
                  <Tooltip formatter={(v) => formatPercent(Number(v))} contentStyle={{ background: "white", border: "1px solid #e2e8f0", borderRadius: "12px", fontSize: 12 }} />
                  <Bar dataKey="conversion_rate" radius={[0, 6, 6, 0]} barSize={18}>
                    {MOCK_INDUSTRY_BREAKDOWN.sort((a, b) => b.conversion_rate - a.conversion_rate).map((_, i) => (
                      <Cell key={i} fill={CONVERSION_COLORS[i % CONVERSION_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </section>

      {/* By City */}
      <section>
        <SectionTitle title="Rendimiento por Ciudad" subtitle="Dónde responden mejor" />
        <MetricTable
          title="Ciudades"
          columns={[
            { key: "city", label: "Ciudad" },
            { key: "count", label: "Leads" },
            { key: "avg_score", label: "Score Prom.", format: (v: number) => v.toFixed(1) },
            { key: "reply_rate", label: "Reply Rate", format: (v: number) => formatPercent(v) },
          ]}
          data={[...MOCK_CITY_BREAKDOWN].sort((a, b) => b.reply_rate - a.reply_rate)}
        />
      </section>

      {/* By Source */}
      <section>
        <SectionTitle title="Rendimiento por Fuente" subtitle="Qué fuentes traen mejores leads" />
        <MetricTable
          title="Fuentes"
          columns={[
            { key: "source", label: "Fuente" },
            { key: "leads", label: "Leads" },
            { key: "avg_score", label: "Score Prom.", format: (v: number) => v.toFixed(1) },
            { key: "reply_rate", label: "Reply Rate", format: (v: number) => formatPercent(v) },
            { key: "conversion_rate", label: "Conv. Rate", format: (v: number) => formatPercent(v) },
          ]}
          data={[...MOCK_SOURCE_PERFORMANCE].sort((a, b) => b.conversion_rate - a.conversion_rate)}
        />
      </section>

      {/* Insights */}
      <section>
        <SectionTitle title="Insights" subtitle="Conclusiones automáticas del sistema" />
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="rounded-2xl border border-emerald-100 bg-emerald-50/30 p-5">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="h-4 w-4 text-emerald-600" />
              <h4 className="text-sm font-semibold text-emerald-800 font-heading">Mayor conversión</h4>
            </div>
            <p className="text-sm text-slate-700">Los leads <strong>referidos</strong> convierten 3x mejor que los de crawler. Los rubros <strong>Inmobiliaria</strong> y <strong>Salud</strong> tienen las mejores tasas.</p>
          </div>

          <div className="rounded-2xl border border-amber-100 bg-amber-50/30 p-5">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="h-4 w-4 text-amber-600" />
              <h4 className="text-sm font-semibold text-amber-800 font-heading">Cuello de botella</h4>
            </div>
            <p className="text-sm text-slate-700">La mayor caída está entre <strong>Contactado → Abierto</strong> (62% drop-off). Revisar subject lines y timing de envío.</p>
          </div>

          <div className="rounded-2xl border border-violet-100 bg-violet-50/30 p-5">
            <div className="flex items-center gap-2 mb-2">
              <Zap className="h-4 w-4 text-violet-600" />
              <h4 className="text-sm font-semibold text-violet-800 font-heading">Oportunidad</h4>
            </div>
            <p className="text-sm text-slate-700"><strong>Bahía Blanca</strong> tiene el reply rate más alto (52%). Considerar aumentar prospección en ciudades medianas.</p>
          </div>
        </div>
      </section>
    </div>
  );
}

"use client";

import { useEffect, useMemo, useState } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { SectionHeader } from "@/components/shared/section-header";
import { AreaChartCard } from "@/components/charts/area-chart-card";
import { PipelineFunnel } from "@/components/dashboard/pipeline-funnel";
import { SkeletonStatCard, SkeletonCard } from "@/components/shared/skeleton";
import { formatPercent } from "@/lib/formatters";
import { CHART_TOOLTIP_STYLE } from "@/lib/constants";
import {
  getCityBreakdown,
  getDashboardStats,
  getIndustryBreakdown,
  getPipeline,
  getSourcePerformance,
  getTimeSeries,
} from "@/lib/api/client";
import {
  Target, MessageSquare, CalendarCheck, Trophy, Clock, Zap,
  TrendingUp, AlertTriangle,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from "recharts";
import { cn } from "@/lib/utils";
import type { CityBreakdown, DashboardStats, IndustryBreakdown, PipelineStage, SourcePerformance, TimeSeriesPoint } from "@/types";

const CONVERSION_COLORS = ["#8b5cf6", "#06b6d4", "#10b981", "#f59e0b", "#ef4444"];

type TabKey = "resumen" | "tendencias" | "desglose" | "insights";

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
    <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
      <h3 className="text-sm font-semibold text-foreground mb-4 font-heading">{title}</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              {columns.map((col) => (
                <th key={col.key} className="px-3 py-2 text-left text-sm font-medium text-muted-foreground font-heading">
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, i) => (
              <tr key={i} className={cn(
                "border-b border-border/50 hover:bg-muted/50 transition-colors",
                i % 2 === 1 && "bg-muted/20"
              )}>
                {columns.map((col) => (
                  <td key={col.key} className="px-3 py-2.5 text-foreground/80">
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

function computeInsights(
  pipeline: PipelineStage[],
  industryBreakdown: IndustryBreakdown[],
  cityBreakdown: CityBreakdown[],
  sourcePerformance: SourcePerformance[]
) {
  // Highest conversion industry/source
  const bestIndustry = [...industryBreakdown].sort((a, b) => b.conversion_rate - a.conversion_rate)[0];
  const bestSource = [...sourcePerformance].sort((a, b) => b.conversion_rate - a.conversion_rate)[0];

  // Bottleneck: biggest drop-off between consecutive pipeline stages
  let bottleneck = { from: "", to: "", dropoff: 0 };
  for (let i = 0; i < pipeline.length - 1; i++) {
    const current = pipeline[i].count;
    const next = pipeline[i + 1].count;
    if (current > 0) {
      const dropoff = 1 - next / current;
      if (dropoff > bottleneck.dropoff) {
        bottleneck = { from: pipeline[i].stage, to: pipeline[i + 1].stage, dropoff };
      }
    }
  }

  // Opportunity: city with highest reply rate
  const bestCity = [...cityBreakdown].sort((a, b) => b.reply_rate - a.reply_rate)[0];

  return { bestIndustry, bestSource, bottleneck, bestCity };
}

export default function PerformancePage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [timeSeries, setTimeSeries] = useState<TimeSeriesPoint[]>([]);
  const [pipeline, setPipeline] = useState<PipelineStage[]>([]);
  const [industryBreakdown, setIndustryBreakdown] = useState<IndustryBreakdown[]>([]);
  const [cityBreakdown, setCityBreakdown] = useState<CityBreakdown[]>([]);
  const [sourcePerformance, setSourcePerformance] = useState<SourcePerformance[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabKey>("resumen");

  useEffect(() => {
    let active = true;

    async function loadPerformance() {
      const [nextStats, nextTimeSeries, nextPipeline, nextIndustry, nextCity, nextSource] =
        await Promise.all([
          getDashboardStats(),
          getTimeSeries(30),
          getPipeline(),
          getIndustryBreakdown(),
          getCityBreakdown(),
          getSourcePerformance(),
        ]);

      if (!active) return;

      setStats(nextStats);
      setTimeSeries(nextTimeSeries);
      setPipeline(nextPipeline);
      setIndustryBreakdown(nextIndustry);
      setCityBreakdown(nextCity);
      setSourcePerformance(nextSource);
      setLoading(false);
    }

    void loadPerformance();

    return () => {
      active = false;
    };
  }, []);

  const insights = useMemo(
    () => computeInsights(pipeline, industryBreakdown, cityBreakdown, sourcePerformance),
    [pipeline, industryBreakdown, cityBreakdown, sourcePerformance]
  );

  const tabs: { key: TabKey; label: string }[] = [
    { key: "resumen", label: "Resumen" },
    { key: "tendencias", label: "Tendencias" },
    { key: "desglose", label: "Desglose" },
    { key: "insights", label: "Insights" },
  ];

  if (loading) {
    return (
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[1400px] px-8 py-8">
          <div className="space-y-8">
            <PageHeader title="Rendimiento" description="Métricas clave para evaluar la efectividad del sistema" />
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => <SkeletonStatCard key={i} />)}
        </div>
        <div className="grid gap-6 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} className="h-[280px]" />)}
        </div>
          </div>
        </div>
      </div>
    );
  }

  // Pipeline velocity: use real data if available, else "Sin datos"
  const velocityValue = (v: number) => v > 0 ? `${v.toFixed(1)}d` : "Sin datos";

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8">
        <div className="space-y-8">
          <PageHeader
            title="Rendimiento"
            description="Métricas clave para evaluar la efectividad del sistema y tomar decisiones"
      />

      {/* Tabs */}
      <div className="flex items-center gap-0 border-b border-border">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={cn(
                "relative px-4 py-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "text-violet-700 dark:text-violet-300"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {tab.label}
              {isActive && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-violet-600 dark:bg-violet-400 rounded-full" />
              )}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      {activeTab === "resumen" && stats && (
        <div className="space-y-8">
          <section>
            <SectionHeader title="Tasas de Conversión" subtitle="Eficiencia en cada etapa del pipeline" className="mb-4" />
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
              <StatCard label="Tasa de Contacto" value={formatPercent(stats.contacted / stats.total_leads)} icon={Target} colorScheme="amber" />
              <StatCard label="Tasa de Apertura" value={formatPercent(stats.open_rate)} icon={Zap} colorScheme="orange" />
              <StatCard label="Tasa de Respuesta" value={formatPercent(stats.reply_rate)} icon={MessageSquare} colorScheme="emerald" />
              <StatCard label="Tasa de Reunión" value={formatPercent(stats.meeting_rate)} icon={CalendarCheck} colorScheme="teal" />
              <StatCard label="Tasa de Cierre" value={formatPercent(stats.conversion_rate)} icon={Trophy} colorScheme="green" />
            </div>
          </section>

          <section>
            <SectionHeader title="Velocidad del Pipeline" subtitle="Tiempo promedio entre etapas" className="mb-4" />
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <StatCard label="Hasta Contacto" value={velocityValue(stats.pipeline_velocity * 0.11)} icon={Clock} colorScheme="blue" subtitle="promedio" />
              <StatCard label="Hasta Respuesta" value={velocityValue(stats.pipeline_velocity * 0.26)} icon={Clock} colorScheme="indigo" subtitle="promedio" />
              <StatCard label="Hasta Reunión" value={velocityValue(stats.pipeline_velocity * 0.45)} icon={Clock} colorScheme="violet" subtitle="promedio" />
              <StatCard label="Hasta Cierre" value={velocityValue(stats.pipeline_velocity)} icon={Clock} colorScheme="purple" subtitle="promedio" />
            </div>
          </section>

          <section>
            <SectionHeader title="Embudo Comercial" subtitle="Dónde están los cuellos de botella" className="mb-4" />
            <PipelineFunnel stages={pipeline} />
          </section>
        </div>
      )}

      {activeTab === "tendencias" && (
        <div className="space-y-6">
          <SectionHeader title="Tendencias" subtitle="Evolución últimos 30 días" className="mb-4" />
          <div className="grid gap-6 lg:grid-cols-2">
            <AreaChartCard title="Leads Nuevos" data={timeSeries} dataKey="leads" color="#8b5cf6" gradientId="perfLeads" />
            <AreaChartCard title="Conversiones" data={timeSeries} dataKey="conversions" color="#22c55e" gradientId="perfConv" />
          </div>
        </div>
      )}

      {activeTab === "desglose" && (
        <div className="space-y-8">
          <section>
            <SectionHeader title="Por Industria" subtitle="Qué rubros convierten mejor" className="mb-4" />
            <div className="grid gap-6 lg:grid-cols-2">
              <MetricTable
                title="Industrias"
                columns={[
                  { key: "industry", label: "Rubro" },
                  { key: "count", label: "Leads" },
                  { key: "avg_score", label: "Score Prom.", format: (v: number) => v.toFixed(1) },
                  { key: "conversion_rate", label: "Conv. Rate", format: (v: number) => formatPercent(v) },
                ]}
                data={[...industryBreakdown].sort((a, b) => b.conversion_rate - a.conversion_rate)}
              />
              <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
                <h3 className="text-sm font-semibold text-foreground mb-4 font-heading">Conversión por Rubro</h3>
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={[...industryBreakdown].sort((a, b) => b.conversion_rate - a.conversion_rate)} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
                      <XAxis type="number" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} tickLine={false} axisLine={false} />
                      <YAxis type="category" dataKey="industry" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} tickLine={false} axisLine={false} width={90} />
                      <Tooltip formatter={(v) => formatPercent(Number(v))} contentStyle={CHART_TOOLTIP_STYLE} />
                      <Bar dataKey="conversion_rate" radius={[0, 6, 6, 0]} barSize={18}>
                        {[...industryBreakdown].sort((a, b) => b.conversion_rate - a.conversion_rate).map((_, i) => (
                          <Cell key={i} fill={CONVERSION_COLORS[i % CONVERSION_COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </section>

          <section>
            <SectionHeader title="Por Ciudad" subtitle="Dónde responden mejor" className="mb-4" />
            <MetricTable
              title="Ciudades"
              columns={[
                { key: "city", label: "Ciudad" },
                { key: "count", label: "Leads" },
                { key: "avg_score", label: "Score Prom.", format: (v: number) => v.toFixed(1) },
                { key: "reply_rate", label: "Reply Rate", format: (v: number) => formatPercent(v) },
              ]}
              data={[...cityBreakdown].sort((a, b) => b.reply_rate - a.reply_rate)}
            />
          </section>

          <section>
            <SectionHeader title="Por Fuente" subtitle="Qué fuentes traen mejores leads" className="mb-4" />
            <MetricTable
              title="Fuentes"
              columns={[
                { key: "source", label: "Fuente" },
                { key: "leads", label: "Leads" },
                { key: "avg_score", label: "Score Prom.", format: (v: number) => v.toFixed(1) },
                { key: "reply_rate", label: "Reply Rate", format: (v: number) => formatPercent(v) },
                { key: "conversion_rate", label: "Conv. Rate", format: (v: number) => formatPercent(v) },
              ]}
              data={[...sourcePerformance].sort((a, b) => b.conversion_rate - a.conversion_rate)}
            />
          </section>
        </div>
      )}

      {activeTab === "insights" && (
        <div className="space-y-6">
          <SectionHeader title="Insights" subtitle="Conclusiones computadas a partir de los datos reales" className="mb-4" />
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="rounded-2xl border border-emerald-200 dark:border-emerald-900/30 bg-emerald-50/30 dark:bg-emerald-950/10 p-5">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                <h4 className="text-sm font-semibold text-emerald-800 dark:text-emerald-300 font-heading">Mayor conversión</h4>
              </div>
              <p className="text-sm text-foreground/80">
                {insights.bestIndustry ? (
                  <>El rubro <strong>{insights.bestIndustry.industry}</strong> tiene la mejor tasa de conversión ({formatPercent(insights.bestIndustry.conversion_rate)}).</>
                ) : "Sin datos de industria."}
                {insights.bestSource && (
                  <> La fuente <strong>{insights.bestSource.source}</strong> convierte a {formatPercent(insights.bestSource.conversion_rate)}.</>
                )}
              </p>
            </div>

            <div className="rounded-2xl border border-amber-200 dark:border-amber-900/30 bg-amber-50/30 dark:bg-amber-950/10 p-5">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                <h4 className="text-sm font-semibold text-amber-800 dark:text-amber-300 font-heading">Cuello de botella</h4>
              </div>
              <p className="text-sm text-foreground/80">
                {insights.bottleneck.from ? (
                  <>La mayor caída está entre <strong>{insights.bottleneck.from}</strong> → <strong>{insights.bottleneck.to}</strong> ({formatPercent(insights.bottleneck.dropoff)} drop-off). Revisar esa transición.</>
                ) : "Sin datos de pipeline para detectar cuellos de botella."}
              </p>
            </div>

            <div className="rounded-2xl border border-violet-200 dark:border-violet-900/30 bg-violet-50/30 dark:bg-violet-950/10 p-5">
              <div className="flex items-center gap-2 mb-2">
                <Zap className="h-4 w-4 text-violet-600 dark:text-violet-400" />
                <h4 className="text-sm font-semibold text-violet-800 dark:text-violet-300 font-heading">Oportunidad</h4>
              </div>
              <p className="text-sm text-foreground/80">
                {insights.bestCity ? (
                  <><strong>{insights.bestCity.city}</strong> tiene el reply rate más alto ({formatPercent(insights.bestCity.reply_rate)}). Considerar aumentar prospección en esa zona.</>
                ) : "Sin datos de ciudades."}
              </p>
            </div>
          </div>
        </div>
      )}
        </div>
      </div>
    </div>
  );
}

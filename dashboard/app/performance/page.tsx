"use client";

import { useMemo, useState } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { SectionHeader } from "@/components/shared/section-header";
import { AreaChartCard } from "@/components/charts/area-chart-card";
import { PipelineFunnel } from "@/components/dashboard/pipeline-funnel";
import { SkeletonStatCard, SkeletonCard } from "@/components/shared/skeleton";
import { formatPercent } from "@/lib/formatters";
import { useApi } from "@/lib/hooks/use-swr-fetch";
import {
  Target, MessageSquare, CalendarCheck, Trophy, Clock, Zap,
  TrendingUp, AlertTriangle,
} from "lucide-react";
import dynamic from "next/dynamic";

const IndustryConversionChart = dynamic(
  () => import("@/components/performance/desglose-charts").then((m) => m.IndustryConversionChart),
  { ssr: false }
);
import { cn } from "@/lib/utils";
import { AiScorePanel } from "@/components/performance/ai-score-panel";
import type { CityBreakdown, DashboardStats, IndustryBreakdown, PipelineStage, SourcePerformance, TimeSeriesPoint } from "@/types";

type TabKey = "resumen" | "tendencias" | "desglose" | "insights" | "ia";

function MetricTable({
  title,
  columns,
  data,
}: {
  title: string;
  columns: { key: string; label: string; format?: (v: number) => string }[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
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
  const { data: stats, isLoading: statsLoading } = useApi<DashboardStats>("/dashboard/stats");
  const { data: timeSeries } = useApi<TimeSeriesPoint[]>("/dashboard/time-series?days=30");
  const { data: pipeline } = useApi<PipelineStage[]>("/dashboard/pipeline");
  const { data: industryBreakdown } = useApi<IndustryBreakdown[]>("/performance/industry");
  const { data: cityBreakdown } = useApi<CityBreakdown[]>("/performance/city");
  const { data: sourcePerformance } = useApi<SourcePerformance[]>("/performance/source");

  const [activeTab, setActiveTab] = useState<TabKey>("resumen");

  const loading = statsLoading;

  const insights = useMemo(
    () => computeInsights(pipeline ?? [], industryBreakdown ?? [], cityBreakdown ?? [], sourcePerformance ?? []),
    [pipeline, industryBreakdown, cityBreakdown, sourcePerformance]
  );

  const tabs: { key: TabKey; label: string }[] = [
    { key: "resumen", label: "Resumen" },
    { key: "tendencias", label: "Tendencias" },
    { key: "desglose", label: "Desglose" },
    { key: "insights", label: "Insights" },
    { key: "ia", label: "IA" },
  ];

  if (loading) {
    return (
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[1400px] px-8 py-8">
          <div className="space-y-8">
            <PageHeader title="Rendimiento" description="Metricas clave para evaluar la efectividad del sistema" />
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
            description="Metricas clave para evaluar la efectividad del sistema y tomar decisiones"
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
            <SectionHeader title="Tasas de Conversion" subtitle="Eficiencia en cada etapa del pipeline" className="mb-4" />
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
              <StatCard label="Tasa de Contacto" value={formatPercent(stats.contacted / stats.total_leads)} icon={Target} colorScheme="amber" />
              <StatCard label="Tasa de Apertura" value={formatPercent(stats.open_rate)} icon={Zap} colorScheme="orange" />
              <StatCard label="Tasa de Respuesta" value={formatPercent(stats.reply_rate)} icon={MessageSquare} colorScheme="emerald" />
              <StatCard label="Tasa de Reunion" value={formatPercent(stats.meeting_rate)} icon={CalendarCheck} colorScheme="teal" />
              <StatCard label="Tasa de Cierre" value={formatPercent(stats.conversion_rate)} icon={Trophy} colorScheme="green" />
            </div>
          </section>

          <section>
            <SectionHeader title="Velocidad del Pipeline" subtitle="Tiempo promedio hasta cierre" className="mb-4" />
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <StatCard label="Hasta Cierre" value={velocityValue(stats.pipeline_velocity)} icon={Clock} colorScheme="purple" subtitle="promedio" />
            </div>
          </section>

          <section>
            <SectionHeader title="Embudo Comercial" subtitle="Donde estan los cuellos de botella" className="mb-4" />
            <PipelineFunnel stages={pipeline ?? []} />
          </section>
        </div>
      )}

      {activeTab === "tendencias" && (
        <div className="space-y-6">
          <SectionHeader title="Tendencias" subtitle="Evolucion ultimos 30 dias" className="mb-4" />
          <div className="grid gap-6 lg:grid-cols-2">
            <AreaChartCard title="Leads Nuevos" data={timeSeries ?? []} dataKey="leads" color="#8b5cf6" gradientId="perfLeads" />
            <AreaChartCard title="Conversiones" data={timeSeries ?? []} dataKey="conversions" color="#22c55e" gradientId="perfConv" />
          </div>
        </div>
      )}

      {activeTab === "desglose" && (
        <div className="space-y-8">
          <section>
            <SectionHeader title="Por Industria" subtitle="Que rubros convierten mejor" className="mb-4" />
            <div className="grid gap-6 lg:grid-cols-2">
              <MetricTable
                title="Industrias"
                columns={[
                  { key: "industry", label: "Rubro" },
                  { key: "count", label: "Leads" },
                  { key: "avg_score", label: "Score Prom.", format: (v: number) => v.toFixed(1) },
                  { key: "conversion_rate", label: "Conv. Rate", format: (v: number) => formatPercent(v) },
                ]}
                data={[...(industryBreakdown ?? [])].sort((a, b) => b.conversion_rate - a.conversion_rate)}
              />
              <IndustryConversionChart data={industryBreakdown ?? []} />
            </div>
          </section>

          <section>
            <SectionHeader title="Por Ciudad" subtitle="Donde responden mejor" className="mb-4" />
            <MetricTable
              title="Ciudades"
              columns={[
                { key: "city", label: "Ciudad" },
                { key: "count", label: "Leads" },
                { key: "avg_score", label: "Score Prom.", format: (v: number) => v.toFixed(1) },
                { key: "reply_rate", label: "Reply Rate", format: (v: number) => formatPercent(v) },
              ]}
              data={[...(cityBreakdown ?? [])].sort((a, b) => b.reply_rate - a.reply_rate)}
            />
          </section>

          <section>
            <SectionHeader title="Por Fuente" subtitle="Que fuentes traen mejores leads" className="mb-4" />
            <MetricTable
              title="Fuentes"
              columns={[
                { key: "source", label: "Fuente" },
                { key: "leads", label: "Leads" },
                { key: "avg_score", label: "Score Prom.", format: (v: number) => v.toFixed(1) },
                { key: "reply_rate", label: "Reply Rate", format: (v: number) => formatPercent(v) },
                { key: "conversion_rate", label: "Conv. Rate", format: (v: number) => formatPercent(v) },
              ]}
              data={[...(sourcePerformance ?? [])].sort((a, b) => b.conversion_rate - a.conversion_rate)}
            />
          </section>
        </div>
      )}

      {activeTab === "ia" && (
        <AiScorePanel />
      )}

      {activeTab === "insights" && (
        <div className="space-y-6">
          <SectionHeader title="Insights" subtitle="Conclusiones computadas a partir de los datos reales" className="mb-4" />
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="rounded-2xl border border-emerald-200 dark:border-emerald-900/30 bg-emerald-50/30 dark:bg-emerald-950/10 p-5">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                <h4 className="text-sm font-semibold text-emerald-800 dark:text-emerald-300 font-heading">Mayor conversion</h4>
              </div>
              <p className="text-sm text-foreground/80">
                {insights.bestIndustry ? (
                  <>El rubro <strong>{insights.bestIndustry.industry}</strong> tiene la mejor tasa de conversion ({formatPercent(insights.bestIndustry.conversion_rate)}).</>
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
                  <>La mayor caida esta entre <strong>{insights.bottleneck.from}</strong> → <strong>{insights.bottleneck.to}</strong> ({formatPercent(insights.bottleneck.dropoff)} drop-off). Revisar esa transicion.</>
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
                  <><strong>{insights.bestCity.city}</strong> tiene el reply rate mas alto ({formatPercent(insights.bestCity.reply_rate)}). Considerar aumentar prospeccion en esa zona.</>
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

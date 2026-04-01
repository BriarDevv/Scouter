"use client";

import { useCallback, useEffect, useState } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { StatsGrid } from "@/components/dashboard/stats-grid";
import { PipelineFunnel } from "@/components/dashboard/pipeline-funnel";
import { AreaChartCard } from "@/components/charts/area-chart-card";
import { IndustryChart } from "@/components/dashboard/industry-chart";
import { RecentActivity } from "@/components/dashboard/recent-activity";
import { ControlCenter } from "@/components/dashboard/control-center";
import { CollapsibleSection } from "@/components/shared/collapsible-section";
import { SkeletonStatCard, SkeletonCard } from "@/components/shared/skeleton";
import { useSystemHealth } from "@/lib/hooks/use-system-health";
import {
  getDashboardStats,
  getIndustryBreakdown,
  getOutreachLogs,
  getPipeline,
  getTimeSeries,
} from "@/lib/api/client";
import type { DashboardStats, IndustryBreakdown, OutreachLog, PipelineStage, TimeSeriesPoint } from "@/types";
import { TerritorySummary } from "@/components/dashboard/territory-summary";
import { sileo } from "sileo";

export default function OverviewPage() {
  const { components, loading: healthLoading, refresh: refreshHealth } = useSystemHealth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [pipeline, setPipeline] = useState<PipelineStage[]>([]);
  const [timeSeries, setTimeSeries] = useState<TimeSeriesPoint[]>([]);
  const [industryBreakdown, setIndustryBreakdown] = useState<IndustryBreakdown[]>([]);
  const [logs, setLogs] = useState<OutreachLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadOverview = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const [nextStats, nextPipeline, nextTimeSeries, nextIndustryBreakdown, nextLogs] =
        await Promise.all([
          getDashboardStats(),
          getPipeline(),
          getTimeSeries(30),
          getIndustryBreakdown(),
          getOutreachLogs({ limit: 8 }),
        ]);

      setStats(nextStats);
      setPipeline(nextPipeline);
      setTimeSeries(nextTimeSeries);
      setIndustryBreakdown(nextIndustryBreakdown);
      setLogs(nextLogs);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Error desconocido";
      setError(message);
      sileo.error({
        title: "Error al cargar el panel",
        description: message,
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadOverview();
  }, [loadOverview]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Panel general"
        description="Estado general del sistema de prospección"
      />

      <ControlCenter health={components} healthLoading={healthLoading} onRefreshHealth={refreshHealth} />

      {/* Error state */}
      {error && !loading && (
        <div className="rounded-lg border border-destructive/40 bg-destructive/10 p-6 text-center space-y-3">
          <p className="text-sm font-medium text-destructive">
            No se pudo cargar el panel
          </p>
          <p className="text-xs text-muted-foreground">{error}</p>
          <button
            onClick={() => void loadOverview()}
            className="inline-flex items-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 transition-colors"
          >
            Reintentar
          </button>
        </div>
      )}

      {/* Key Metrics */}
      {loading ? (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => <SkeletonStatCard key={i} />)}
        </div>
      ) : (
        <StatsGrid stats={stats!} />
      )}

      {/* Charts & Data */}
      {loading ? (
        <div className="grid gap-6 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} className="h-[280px]" />)}
        </div>
      ) : (
        <>
          <CollapsibleSection title="Tendencias" defaultOpen>
            <div className="grid gap-6 lg:grid-cols-3">
              <AreaChartCard
                title="Leads por Día"
                subtitle="Últimos 30 días"
                data={timeSeries}
                dataKey="leads"
                color="#8b5cf6"
                gradientId="leadsGrad"
              />
              <AreaChartCard
                title="Outreach por Día"
                subtitle="Emails enviados"
                data={timeSeries}
                dataKey="outreach"
                color="#06b6d4"
                gradientId="outreachGrad"
              />
              <AreaChartCard
                title="Respuestas por Día"
                subtitle="Replies recibidos"
                data={timeSeries}
                dataKey="replies"
                color="#10b981"
                gradientId="repliesGrad"
              />
            </div>
          </CollapsibleSection>

          <CollapsibleSection title="Pipeline & Distribución" defaultOpen>
            <div className="grid gap-6 lg:grid-cols-2">
              <PipelineFunnel stages={pipeline} />
              <IndustryChart data={industryBreakdown} />
            </div>
          </CollapsibleSection>

          <CollapsibleSection title="Actividad Reciente" defaultOpen={false}>
            <RecentActivity logs={logs} />
          </CollapsibleSection>
        </>
      )}

      <TerritorySummary />
    </div>
  );
}

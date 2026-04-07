"use client";

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
import { useApi } from "@/lib/hooks/use-swr-fetch";
import type { DashboardStats, IndustryBreakdown, OutreachLog, PipelineStage, TimeSeriesPoint } from "@/types";
import { AiHealthCard } from "@/components/dashboard/ai-health-card";
import { TopCorrections } from "@/components/dashboard/top-corrections";
import { TerritorySummary } from "@/components/dashboard/territory-summary";

export default function PanelPage() {
  const { components, loading: healthLoading, refresh: refreshHealth } = useSystemHealth();
  const { data: stats, isLoading: statsLoading, error: statsError, mutate: mutateStats } = useApi<DashboardStats>("/dashboard/stats");
  const { data: pipeline, mutate: mutatePipeline } = useApi<PipelineStage[]>("/dashboard/pipeline");
  const { data: timeSeries, mutate: mutateTimeSeries } = useApi<TimeSeriesPoint[]>("/dashboard/time-series?days=30");
  const { data: industryBreakdown, mutate: mutateIndustry } = useApi<IndustryBreakdown[]>("/performance/industry");
  const { data: logs, mutate: mutateLogs } = useApi<OutreachLog[]>("/outreach/logs?limit=8");

  const loading = statsLoading;
  const error = statsError ? (statsError instanceof Error ? statsError.message : "Error desconocido") : null;

  async function handleRetry() {
    await Promise.all([mutateStats(), mutatePipeline(), mutateTimeSeries(), mutateIndustry(), mutateLogs()]);
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8">
        <div className="space-y-6">
          <PageHeader
            title="Panel general"
            description="Estado general del sistema de prospeccion"
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
                onClick={() => void handleRetry()}
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
          ) : stats ? (
            <StatsGrid stats={stats} />
          ) : null}

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
                    title="Leads por Dia"
                    subtitle="Ultimos 30 dias"
                    data={timeSeries ?? []}
                    dataKey="leads"
                    color="#8b5cf6"
                    gradientId="leadsGrad"
                  />
                  <AreaChartCard
                    title="Outreach por Dia"
                    subtitle="Emails enviados"
                    data={timeSeries ?? []}
                    dataKey="outreach"
                    color="#06b6d4"
                    gradientId="outreachGrad"
                  />
                  <AreaChartCard
                    title="Respuestas por Dia"
                    subtitle="Replies recibidos"
                    data={timeSeries ?? []}
                    dataKey="replies"
                    color="#10b981"
                    gradientId="repliesGrad"
                  />
                </div>
              </CollapsibleSection>

              <CollapsibleSection title="Pipeline & Distribucion" defaultOpen>
                <div className="grid gap-6 lg:grid-cols-2">
                  <PipelineFunnel stages={pipeline ?? []} />
                  <IndustryChart data={industryBreakdown ?? []} />
                </div>
              </CollapsibleSection>

              <CollapsibleSection title="Actividad Reciente" defaultOpen={false}>
                <RecentActivity logs={logs ?? []} />
              </CollapsibleSection>
            </>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <AiHealthCard />
            <TopCorrections />
          </div>

          <TerritorySummary />
        </div>
      </div>
    </div>
  );
}

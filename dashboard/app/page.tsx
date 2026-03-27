"use client";

import { useEffect, useState } from "react";
import { ChevronDown } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { StatsGrid } from "@/components/dashboard/stats-grid";
import { PipelineFunnel } from "@/components/dashboard/pipeline-funnel";
import { AreaChartCard } from "@/components/charts/area-chart-card";
import { IndustryChart } from "@/components/dashboard/industry-chart";
import { RecentActivity } from "@/components/dashboard/recent-activity";
import { SystemHealthStrip } from "@/components/dashboard/system-health-strip";
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

export default function OverviewPage() {
  const { health, components, loading: healthLoading, error: healthError } = useSystemHealth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [pipeline, setPipeline] = useState<PipelineStage[]>([]);
  const [timeSeries, setTimeSeries] = useState<TimeSeriesPoint[]>([]);
  const [industryBreakdown, setIndustryBreakdown] = useState<IndustryBreakdown[]>([]);
  const [logs, setLogs] = useState<OutreachLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function loadOverview() {
      const [nextStats, nextPipeline, nextTimeSeries, nextIndustryBreakdown, nextLogs] =
        await Promise.all([
          getDashboardStats(),
          getPipeline(),
          getTimeSeries(30),
          getIndustryBreakdown(),
          getOutreachLogs({ limit: 8 }),
        ]);

      if (!active) return;

      setStats(nextStats);
      setPipeline(nextPipeline);
      setTimeSeries(nextTimeSeries);
      setIndustryBreakdown(nextIndustryBreakdown);
      setLogs(nextLogs);
      setLoading(false);
    }

    void loadOverview();

    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Panel general"
        description="Estado general del sistema de prospección"
      />

      <SystemHealthStrip health={health} loading={healthLoading} error={healthError} />

      <ControlCenter health={components} />

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

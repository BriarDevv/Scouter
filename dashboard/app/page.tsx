"use client";

import { PageHeader } from "@/components/layout/page-header";
import { StatsGrid } from "@/components/dashboard/stats-grid";
import { PipelineFunnel } from "@/components/dashboard/pipeline-funnel";
import { AreaChartCard } from "@/components/charts/area-chart-card";
import { IndustryChart } from "@/components/dashboard/industry-chart";
import { RecentActivity } from "@/components/dashboard/recent-activity";
import {
  MOCK_STATS,
  MOCK_PIPELINE,
  MOCK_TIME_SERIES,
  MOCK_INDUSTRY_BREAKDOWN,
  MOCK_LOGS,
} from "@/data/mock";

export default function OverviewPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Overview"
        description="Estado general del sistema de prospección"
      />

      <StatsGrid stats={MOCK_STATS} />

      <div className="grid gap-6 lg:grid-cols-2">
        <AreaChartCard
          title="Leads por Día"
          subtitle="Últimos 30 días"
          data={MOCK_TIME_SERIES}
          dataKey="leads"
          color="#8b5cf6"
          gradientId="leadsGrad"
        />
        <AreaChartCard
          title="Outreach por Día"
          subtitle="Emails enviados"
          data={MOCK_TIME_SERIES}
          dataKey="outreach"
          color="#06b6d4"
          gradientId="outreachGrad"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <PipelineFunnel stages={MOCK_PIPELINE} />
        <IndustryChart data={MOCK_INDUSTRY_BREAKDOWN} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <AreaChartCard
          title="Respuestas por Día"
          subtitle="Replies recibidos"
          data={MOCK_TIME_SERIES}
          dataKey="replies"
          color="#10b981"
          gradientId="repliesGrad"
        />
        <RecentActivity logs={MOCK_LOGS} />
      </div>
    </div>
  );
}

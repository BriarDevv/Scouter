"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { StatsGrid } from "@/components/dashboard/stats-grid";
import { PipelineFunnel } from "@/components/dashboard/pipeline-funnel";
import { AreaChartCard } from "@/components/charts/area-chart-card";
import { IndustryChart } from "@/components/dashboard/industry-chart";
import { RecentActivity } from "@/components/dashboard/recent-activity";
import {
  getDashboardStats,
  getLeads,
  getIndustryBreakdown,
  getOutreachLogs,
  getPipeline,
  getTimeSeries,
} from "@/lib/api/client";
import {
  MOCK_LEADS,
  MOCK_STATS,
  MOCK_PIPELINE,
  MOCK_TIME_SERIES,
  MOCK_INDUSTRY_BREAKDOWN,
  MOCK_LOGS,
} from "@/data/mock";

export default function OverviewPage() {
  const [stats, setStats] = useState(MOCK_STATS);
  const [pipeline, setPipeline] = useState(MOCK_PIPELINE);
  const [timeSeries, setTimeSeries] = useState(MOCK_TIME_SERIES);
  const [industryBreakdown, setIndustryBreakdown] = useState(MOCK_INDUSTRY_BREAKDOWN);
  const [logs, setLogs] = useState(MOCK_LOGS);
  const [leads, setLeads] = useState(MOCK_LEADS);

  useEffect(() => {
    let active = true;

    async function loadOverview() {
      const [nextStats, nextPipeline, nextTimeSeries, nextIndustryBreakdown, nextLogs, nextLeads] =
        await Promise.all([
          getDashboardStats(),
          getPipeline(),
          getTimeSeries(30),
          getIndustryBreakdown(),
          getOutreachLogs({ limit: 8 }),
          getLeads({ page: 1, page_size: 200 }),
        ]);

      if (!active) {
        return;
      }

      setStats(nextStats);
      setPipeline(nextPipeline);
      setTimeSeries(nextTimeSeries);
      setIndustryBreakdown(nextIndustryBreakdown);
      setLogs(nextLogs);
      setLeads(nextLeads.items);
    }

    void loadOverview();

    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="space-y-8">
      <PageHeader
        title="Overview"
        description="Estado general del sistema de prospección"
      />

      <StatsGrid stats={stats} />

      <div className="grid gap-6 lg:grid-cols-2">
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
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <PipelineFunnel stages={pipeline} />
        <IndustryChart data={industryBreakdown} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <AreaChartCard
          title="Respuestas por Día"
          subtitle="Replies recibidos"
          data={timeSeries}
          dataKey="replies"
          color="#10b981"
          gradientId="repliesGrad"
        />
        <RecentActivity logs={logs} leads={leads} />
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { CalendarCheck, Inbox, MessageSquare, Sparkles, Ticket } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { StatsGrid } from "@/components/dashboard/stats-grid";
import { PipelineFunnel } from "@/components/dashboard/pipeline-funnel";
import { AreaChartCard } from "@/components/charts/area-chart-card";
import { IndustryChart } from "@/components/dashboard/industry-chart";
import { RecentActivity } from "@/components/dashboard/recent-activity";
import { StatCard } from "@/components/shared/stat-card";
import {
  getDashboardStats,
  getInboundMessages,
  getLeads,
  getIndustryBreakdown,
  getOutreachLogs,
  getPipeline,
  getTimeSeries,
} from "@/lib/api/client";
import { POSITIVE_REPLY_LABELS } from "@/lib/constants";
import {
  MOCK_DRAFTS,
  MOCK_LEADS,
  MOCK_STATS,
  MOCK_PIPELINE,
  MOCK_TIME_SERIES,
  MOCK_INDUSTRY_BREAKDOWN,
  MOCK_LOGS,
} from "@/data/mock";
import type { InboundMessage } from "@/types";

export default function OverviewPage() {
  const [stats, setStats] = useState(MOCK_STATS);
  const [pipeline, setPipeline] = useState(MOCK_PIPELINE);
  const [timeSeries, setTimeSeries] = useState(MOCK_TIME_SERIES);
  const [industryBreakdown, setIndustryBreakdown] = useState(MOCK_INDUSTRY_BREAKDOWN);
  const [logs, setLogs] = useState(MOCK_LOGS);
  const [leads, setLeads] = useState(MOCK_LEADS);
  const [inboundMessages, setInboundMessages] = useState<InboundMessage[]>([]);
  const [inboundError, setInboundError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadOverview() {
      const [nextStats, nextPipeline, nextTimeSeries, nextIndustryBreakdown, nextLogs, nextLeads, nextInbound] =
        await Promise.all([
          getDashboardStats(),
          getPipeline(),
          getTimeSeries(30),
          getIndustryBreakdown(),
          getOutreachLogs({ limit: 8 }),
          getLeads({ page: 1, page_size: 200 }),
          getInboundMessages({ limit: 100 }).catch((error) => {
            console.warn("Unable to load inbound messages for overview", error);
            return null;
          }),
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
      if (nextInbound) {
        setInboundMessages(nextInbound);
        setInboundError(null);
      } else {
        setInboundMessages([]);
        setInboundError("No se pudieron cargar las replies inbound del overview.");
      }
    }

    void loadOverview();

    return () => {
      active = false;
    };
  }, []);

  const repliedLeadCount = new Set(
    inboundMessages.map((message) => message.lead_id).filter(Boolean)
  ).size;
  const positiveRepliesCount = inboundMessages.filter(
    (message) => message.classification_label && POSITIVE_REPLY_LABELS.includes(message.classification_label)
  ).length;
  const quoteIntentCount = inboundMessages.filter(
    (message) => message.classification_label === "asked_for_quote"
  ).length;
  const meetingIntentCount = inboundMessages.filter(
    (message) => message.classification_label === "asked_for_meeting"
  ).length;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Panel general"
        description="Estado general del sistema de prospección"
      />

      <StatsGrid stats={stats} />

      <div className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="font-heading text-base font-semibold text-foreground">Canal mail</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Replies inbound reales y clasificados sobre el inbox comercial.
            </p>
          </div>
          {inboundError && (
            <span className="rounded-full bg-rose-50 dark:bg-rose-950/30 px-3 py-1 text-xs font-medium text-rose-700">
              Inbox no disponible
            </span>
          )}
        </div>
        <div className="grid grid-cols-2 gap-4 xl:grid-cols-5">
          <StatCard
            label="Replies recientes"
            value={inboundMessages.length}
            icon={Inbox}
            iconBg="bg-violet-50"
            iconColor="text-violet-600"
          />
          <StatCard
            label="Leads que respondieron"
            value={repliedLeadCount}
            icon={MessageSquare}
            iconBg="bg-emerald-50"
            iconColor="text-emerald-600"
          />
          <StatCard
            label="Replies positivas"
            value={positiveRepliesCount}
            icon={Sparkles}
            iconBg="bg-cyan-50"
            iconColor="text-cyan-600"
          />
          <StatCard
            label="Intención de cotizar"
            value={quoteIntentCount}
            icon={Ticket}
            iconBg="bg-blue-50"
            iconColor="text-blue-600"
          />
          <StatCard
            label="Intención de reunión"
            value={meetingIntentCount}
            icon={CalendarCheck}
            iconBg="bg-teal-50"
            iconColor="text-teal-600"
          />
        </div>
      </div>

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

"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, CalendarCheck, Inbox, MessageSquare, RefreshCw, Sparkles } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { StatsGrid } from "@/components/dashboard/stats-grid";
import { PipelineFunnel } from "@/components/dashboard/pipeline-funnel";
import { AreaChartCard } from "@/components/charts/area-chart-card";
import { IndustryChart } from "@/components/dashboard/industry-chart";
import { RecentActivity } from "@/components/dashboard/recent-activity";
import { StatCard } from "@/components/shared/stat-card";
import { SectionHeader } from "@/components/shared/section-header";
import { CollapsibleSection } from "@/components/shared/collapsible-section";
import { SkeletonStatCard, SkeletonCard } from "@/components/shared/skeleton";
import { Button } from "@/components/ui/button";
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
  const [loading, setLoading] = useState(true);

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

      if (!active) return;

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
      setLoading(false);
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

      {/* Group 1: Key Metrics */}
      {loading ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => <SkeletonStatCard key={i} />)}
          </div>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => <SkeletonStatCard key={i} />)}
          </div>
        </div>
      ) : (
        <StatsGrid stats={stats} />
      )}

      {/* Group 2: Canal Mail */}
      <div className="space-y-4">
        <SectionHeader
          title="Canal mail"
          subtitle="Replies inbound reales y clasificados sobre el inbox comercial."
          action={
            inboundError ? (
              <div className="flex items-center gap-2 rounded-xl border border-rose-200 dark:border-rose-900/30 bg-rose-50 dark:bg-rose-950/20 px-3 py-2">
                <AlertTriangle className="h-4 w-4 text-rose-600 dark:text-rose-400" />
                <span className="text-xs font-medium text-rose-700 dark:text-rose-300">Inbox no disponible</span>
                <Button variant="ghost" size="sm" className="h-6 rounded-lg px-2 text-xs text-rose-600" onClick={() => window.location.reload()}>
                  <RefreshCw className="h-3 w-3 mr-1" /> Reintentar
                </Button>
              </div>
            ) : undefined
          }
        />
        {loading ? (
          <div className="grid grid-cols-2 gap-4 xl:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => <SkeletonStatCard key={i} />)}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4 xl:grid-cols-3">
            <StatCard
              label="Replies recientes"
              value={inboundMessages.length}
              icon={Inbox}
              colorScheme="violet"
              href="/responses"
            />
            <StatCard
              label="Positivas"
              value={positiveRepliesCount}
              icon={Sparkles}
              colorScheme="cyan"
              subtitle={`${quoteIntentCount} cotización · ${meetingIntentCount} reunión`}
            />
            <StatCard
              label="Leads que respondieron"
              value={repliedLeadCount}
              icon={MessageSquare}
              colorScheme="emerald"
            />
          </div>
        )}
      </div>

      {/* Group 3: Trends & Pipeline */}
      {loading ? (
        <div className="grid gap-6 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} className="h-[280px]" />)}
        </div>
      ) : (
        <>
          <CollapsibleSection title="Tendencias" defaultOpen>
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
          </CollapsibleSection>

          <CollapsibleSection title="Pipeline & Distribución" defaultOpen>
            <div className="grid gap-6 lg:grid-cols-2">
              <PipelineFunnel stages={pipeline} />
              <IndustryChart data={industryBreakdown} />
            </div>
          </CollapsibleSection>

          <CollapsibleSection title="Respuestas & Actividad" defaultOpen>
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
          </CollapsibleSection>
        </>
      )}
    </div>
  );
}

"use client";

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Skeleton, SkeletonCard } from "@/components/shared/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import {
  getCommercialBrief,
  getDrafts,
  getInboundMessages,
  getInboundThreads,
  getLeadById,
  getLeadResearch,
  getOutreachLogs,
  getPipelineRuns,
} from "@/lib/api/client";
import type {
  CommercialBrief,
  OutreachDraft,
  OutreachLog,
  EmailThreadSummary,
  InboundMessage,
  Lead,
  LeadResearchReport,
  PipelineRunSummary,
  TaskStatusRecord,
} from "@/types";
import { ArrowLeft, FileText } from "lucide-react";

import { LeadContactCard } from "@/components/leads/lead-contact-card";
import { LeadDetailHeader } from "@/components/leads/lead-detail-header";
import { LeadContextPanel } from "@/components/leads/lead-context-panel";
import { useLeadActions } from "@/components/leads/lead-actions";

function LeadDetailSkeleton() {
  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8">
        <div className="space-y-6">
          <Skeleton className="h-8 w-32" />
          <div className="flex items-start justify-between">
            <div className="space-y-2">
              <Skeleton className="h-8 w-64" />
              <Skeleton className="h-4 w-48" />
            </div>
            <div className="flex gap-2">
              <Skeleton className="h-9 w-24 rounded-xl" />
              <Skeleton className="h-9 w-32 rounded-xl" />
              <Skeleton className="h-9 w-24 rounded-xl" />
            </div>
          </div>
          <div className="grid gap-6 lg:grid-cols-3">
            <div className="space-y-6 lg:col-span-1">
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
            </div>
            <div className="space-y-6 lg:col-span-2">
              <SkeletonCard className="h-40" />
              <SkeletonCard className="h-48" />
              <SkeletonCard className="h-32" />
              <SkeletonCard className="h-32" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function LeadDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [lead, setLead] = useState<Lead | null>(null);
  const [drafts, setDrafts] = useState<OutreachDraft[]>([]);
  const [logs, setLogs] = useState<OutreachLog[]>([]);
  const [pipelineRuns, setPipelineRuns] = useState<PipelineRunSummary[]>([]);
  const [inboundMessages, setInboundMessages] = useState<InboundMessage[]>([]);
  const [inboundThreads, setInboundThreads] = useState<EmailThreadSummary[]>([]);
  const [latestTask, setLatestTask] = useState<TaskStatusRecord | null>(null);
  const [isMissing, setIsMissing] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [research, setResearch] = useState<LeadResearchReport | null>(null);
  const [brief, setBrief] = useState<CommercialBrief | null>(null);

  const refreshLeadContext = useCallback(async () => {
    const [nextLead, nextDrafts, nextLogs, nextPipelineRuns, nextInboundMessages, nextInboundThreads, nextResearch, nextBrief] = await Promise.all([
      getLeadById(id),
      getDrafts({ lead_id: id }),
      getOutreachLogs({ lead_id: id, limit: 20 }),
      getPipelineRuns({ lead_id: id, limit: 5 }),
      getInboundMessages({ lead_id: id, limit: 20 }).catch(() => []),
      getInboundThreads({ lead_id: id, limit: 10 }).catch(() => []),
      getLeadResearch(id).catch(() => null),
      getCommercialBrief(id).catch(() => null),
    ]);
    setLead(nextLead);
    setDrafts(nextDrafts);
    setLogs(nextLogs);
    setPipelineRuns(nextPipelineRuns);
    setInboundMessages(nextInboundMessages);
    setInboundThreads(nextInboundThreads);
    setResearch(nextResearch);
    setBrief(nextBrief);
    setIsMissing(false);
  }, [id]);

  useEffect(() => {
    let active = true;

    async function loadLeadContext() {
      try {
        await refreshLeadContext();
        if (!active) return;
      } catch (err) {
        console.warn("Failed to load lead context:", err);
        if (!active) return;
        setLead(null);
        setDrafts([]);
        setLogs([]);
        setPipelineRuns([]);
        setInboundMessages([]);
        setInboundThreads([]);
        setResearch(null);
        setBrief(null);
        setLatestTask(null);
        setIsMissing(true);
      } finally {
        if (active) setIsLoading(false);
      }
    }

    void loadLeadContext();

    return () => {
      active = false;
    };
  }, [refreshLeadContext]);

  const actions = useLeadActions({
    leadId: lead?.id ?? null,
    onRefresh: refreshLeadContext,
    onLatestTask: setLatestTask,
    onResearch: setResearch,
    onBrief: setBrief,
  });

  if (isLoading && !lead) {
    return <LeadDetailSkeleton />;
  }

  if (!lead || isMissing) {
    return (
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[1400px] px-8 py-8">
          <div className="space-y-6">
            <Link href="/leads">
              <Button variant="ghost" size="sm" className="gap-1.5 rounded-xl">
                <ArrowLeft className="h-4 w-4" /> Volver a leads
              </Button>
            </Link>
            <EmptyState
              icon={FileText}
              title="Lead no encontrado"
              description="El lead que buscás no existe o fue eliminado."
            />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8">
        <div className="space-y-6">
          <Link href="/leads">
            <Button variant="ghost" size="sm" className="gap-1.5 rounded-xl">
              <ArrowLeft className="h-4 w-4" /> Volver a leads
            </Button>
          </Link>

          <LeadDetailHeader
            lead={lead}
            isRunningPipeline={actions.isRunningPipeline}
            isReviewingLead={actions.isReviewingLead}
            isGeneratingDraft={actions.isGeneratingDraft}
            isApprovingLead={actions.isApprovingLead}
            onRunPipeline={actions.handleRunPipeline}
            onReviewLead={actions.handleReviewLead}
            onGenerateDraft={actions.handleGenerateDraft}
            onApproveLead={actions.handleApproveLead}
          />

          <div className="grid gap-6 lg:grid-cols-3">
            <LeadContactCard
              lead={lead}
              isRunningPipeline={actions.isRunningPipeline}
              onRunPipeline={actions.handleRunPipeline}
            />

            <LeadContextPanel
              lead={lead}
              research={research}
              brief={brief}
              drafts={drafts}
              logs={logs}
              pipelineRuns={pipelineRuns}
              latestTask={latestTask}
              inboundMessages={inboundMessages}
              inboundThreads={inboundThreads}
              isRunningPipeline={actions.isRunningPipeline}
              isRunningResearch={actions.isRunningResearch}
              isGeneratingBrief={actions.isGeneratingBrief}
              isGeneratingDraft={actions.isGeneratingDraft}
              isReviewingDraftId={actions.isReviewingDraftId}
              onRunPipeline={actions.handleRunPipeline}
              onRunResearch={actions.handleRunResearch}
              onGenerateBrief={actions.handleGenerateBrief}
              onGenerateDraft={actions.handleGenerateDraft}
              onReviewDraft={actions.handleReviewDraft}
              onRefresh={() => void refreshLeadContext()}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

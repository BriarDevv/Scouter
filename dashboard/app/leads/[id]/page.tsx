"use client";

import { use, useCallback } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Skeleton, SkeletonCard } from "@/components/shared/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { useApi } from "@/lib/hooks/use-swr-fetch";
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
import { useState } from "react";

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

  const { data: lead, isLoading: leadLoading, error: leadError, mutate: mutateLead } = useApi<Lead>(`/leads/${id}`);
  const { data: drafts, mutate: mutateDrafts } = useApi<OutreachDraft[]>(`/outreach/drafts?lead_id=${id}`);
  const { data: logs, mutate: mutateLogs } = useApi<OutreachLog[]>(`/outreach/logs?lead_id=${id}&limit=20`);
  const { data: pipelineRuns, mutate: mutatePipelineRuns } = useApi<PipelineRunSummary[]>(`/pipelines/runs?lead_id=${id}&limit=5`);
  const { data: inboundMessages, mutate: mutateInboundMessages } = useApi<InboundMessage[]>(`/mail/inbound/messages?lead_id=${id}&limit=20`);
  const { data: inboundThreads, mutate: mutateInboundThreads } = useApi<EmailThreadSummary[]>(`/mail/inbound/threads?lead_id=${id}&limit=10`);
  const { data: research, mutate: mutateResearch } = useApi<LeadResearchReport | null>(`/leads/${id}/research`);
  const { data: brief, mutate: mutateBrief } = useApi<CommercialBrief | null>(`/briefs/leads/${id}`);

  const [latestTask, setLatestTask] = useState<TaskStatusRecord | null>(null);

  const isLoading = leadLoading;
  const isMissing = !leadLoading && (leadError != null || !lead);

  const refreshLeadContext = useCallback(async () => {
    await Promise.all([
      mutateLead(),
      mutateDrafts(),
      mutateLogs(),
      mutatePipelineRuns(),
      mutateInboundMessages(),
      mutateInboundThreads(),
      mutateResearch(),
      mutateBrief(),
    ]);
  }, [mutateLead, mutateDrafts, mutateLogs, mutatePipelineRuns, mutateInboundMessages, mutateInboundThreads, mutateResearch, mutateBrief]);

  const actions = useLeadActions({
    leadId: lead?.id ?? null,
    onRefresh: refreshLeadContext,
    onLatestTask: setLatestTask,
    onResearch: (r) => void mutateResearch(r, false),
    onBrief: (b) => void mutateBrief(b, false),
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
              description="El lead que buscas no existe o fue eliminado."
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
              research={research ?? null}
              brief={brief ?? null}
              drafts={drafts ?? []}
              logs={logs ?? []}
              pipelineRuns={pipelineRuns ?? []}
              latestTask={latestTask}
              inboundMessages={inboundMessages ?? []}
              inboundThreads={inboundThreads ?? []}
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

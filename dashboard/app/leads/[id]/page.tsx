"use client";

import { use, useCallback, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ScoreBadge } from "@/components/shared/status-badge";
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
import { ArrowLeft, FileText, Briefcase, Loader2, Phone, PhoneOff, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

import { LeadSidebar } from "@/components/leads/lead-sidebar";
import { LeadDetailHeader } from "@/components/leads/lead-detail-header";
import { LeadTabsPanel } from "@/components/leads/lead-tabs-panel";
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

  const { data: lead, isLoading: leadLoading, error: leadError, mutate: mutateLead } = useApi<Lead>(`/leads/${id}`);
  const { data: drafts, mutate: mutateDrafts } = useApi<OutreachDraft[]>(`/outreach/drafts?lead_id=${id}`);
  const { data: logs, mutate: mutateLogs } = useApi<OutreachLog[]>(`/outreach/logs?lead_id=${id}&limit=20`);
  const { data: pipelineRuns, mutate: mutatePipelineRuns } = useApi<PipelineRunSummary[]>(`/pipelines/runs?lead_id=${id}&limit=5`);
  const { data: inboundMessages, mutate: mutateInboundMessages } = useApi<InboundMessage[]>(`/mail/inbound/messages?lead_id=${id}&limit=20`);
  const { data: inboundThreads, mutate: mutateInboundThreads } = useApi<EmailThreadSummary[]>(`/mail/inbound/threads?lead_id=${id}&limit=10`);
  const { data: research, mutate: mutateResearch } = useApi<LeadResearchReport | null>(`/leads/${id}/research`);
  const { data: brief, mutate: mutateBrief } = useApi<CommercialBrief | null>(`/briefs/leads/${id}`);

  const [latestTask, setLatestTask] = useState<TaskStatusRecord | null>(null);
  const [showBrief, setShowBrief] = useState(false);

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
          <LeadDetailHeader
            lead={lead}
            isRunningPipeline={actions.isRunningPipeline}
            isReviewingLead={actions.isReviewingLead}
            isGeneratingDraft={actions.isGeneratingDraft}
            isApprovingLead={actions.isApprovingLead}
            onRunPipeline={actions.handleRunPipeline}
            onReviewLead={actions.handleReviewLead}
            onGenerateDraft={actions.handleGenerateDraft}
            onGenerateWhatsAppDraft={actions.handleGenerateWhatsAppDraft}
            onApproveLead={actions.handleApproveLead}
          />

          {/* Brief toggle */}
          <div>
            <button
              onClick={() => brief ? setShowBrief(!showBrief) : actions.handleGenerateBrief()}
              disabled={actions.isGeneratingBrief}
              className="flex items-center gap-1.5 rounded-xl border border-border px-3 py-2 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            >
              {actions.isGeneratingBrief ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Briefcase className="h-3.5 w-3.5" />}
              {brief ? "Brief" : "Generar Brief"}
              {brief && <ChevronDown className={cn("h-3 w-3 transition-transform", showBrief && "rotate-180")} />}
            </button>
            {showBrief && brief && (brief.status === "generated" || brief.status === "reviewed") && (
              <div className="mt-2 rounded-2xl border border-border bg-card overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Score</th>
                      <th className="text-left px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Budget</th>
                      <th className="text-left px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Scope</th>
                      <th className="text-left px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Prioridad</th>
                      <th className="text-left px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Rango</th>
                      <th className="text-center px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Llamar</th>
                      <th className="text-left px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Canal</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td className="px-4 py-2.5"><ScoreBadge score={brief.opportunity_score} /></td>
                      <td className="px-3 py-2.5">
                        {brief.budget_tier ? (
                          <span className="rounded-full bg-muted px-2.5 py-0.5 text-[10px] font-medium text-foreground capitalize">{brief.budget_tier}</span>
                        ) : <span className="text-[10px] text-muted-foreground/40">—</span>}
                      </td>
                      <td className="px-3 py-2.5 text-xs text-muted-foreground capitalize">{brief.estimated_scope?.replace(/_/g, " ") || "—"}</td>
                      <td className="px-3 py-2.5">
                        <span className={cn(
                          "text-xs font-medium capitalize",
                          brief.contact_priority === "immediate" ? "text-red-600 dark:text-red-400"
                            : brief.contact_priority === "high" ? "text-amber-600 dark:text-amber-400"
                            : "text-muted-foreground"
                        )}>{brief.contact_priority || "—"}</span>
                      </td>
                      <td className="px-3 py-2.5 text-xs text-muted-foreground font-data">
                        {brief.estimated_budget_min != null && brief.estimated_budget_max != null
                          ? `$${brief.estimated_budget_min.toLocaleString()}–${brief.estimated_budget_max.toLocaleString()}`
                          : "—"}
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        {brief.should_call === "yes" ? <Phone className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400 mx-auto" />
                          : brief.should_call === "maybe" ? <Phone className="h-3.5 w-3.5 text-amber-500 mx-auto" />
                          : <PhoneOff className="h-3.5 w-3.5 text-muted-foreground/40 mx-auto" />}
                      </td>
                      <td className="px-3 py-2.5 text-xs text-muted-foreground capitalize">{brief.recommended_contact_method?.replace(/_/g, " ") || "—"}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <LeadTabsPanel
              sidebar={<LeadSidebar lead={lead} />}
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
              isSendingDraftId={actions.isSendingDraftId}
              onRunPipeline={actions.handleRunPipeline}
              onRunResearch={actions.handleRunResearch}
              onGenerateBrief={actions.handleGenerateBrief}
              onGenerateDraft={actions.handleGenerateDraft}
              onReviewDraft={actions.handleReviewDraft}
              onSendDraft={actions.handleSendDraft}
              onRefresh={() => void refreshLeadContext()}
            />
        </div>
      </div>
    </div>
  );
}

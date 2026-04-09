"use client";

import type {
  CommercialBrief,
  Lead,
  LeadResearchReport,
  OutreachDraft,
  OutreachLog,
  InboundMessage,
  EmailThreadSummary,
  PipelineRunSummary,
  TaskStatusRecord,
} from "@/types";

import { LeadAnalysisSection } from "@/components/leads/lead-analysis-section";
import { LeadDossierSection } from "@/components/leads/lead-dossier-section";
import { LeadBriefSection } from "@/components/leads/lead-brief-section";
import { LeadOutreachSection } from "@/components/leads/lead-outreach-section";
import { AiDecisionsPanel } from "@/components/leads/ai-decisions-panel";
import { LeadPipelineSection } from "@/components/leads/lead-pipeline-section";
import { LeadRepliesSection } from "@/components/leads/lead-replies-section";
import { LeadTimelineSection } from "@/components/leads/lead-timeline-section";

interface LeadContextPanelProps {
  lead: Lead;
  research: LeadResearchReport | null;
  brief: CommercialBrief | null;
  drafts: OutreachDraft[];
  logs: OutreachLog[];
  pipelineRuns: PipelineRunSummary[];
  latestTask: TaskStatusRecord | null;
  inboundMessages: InboundMessage[];
  inboundThreads: EmailThreadSummary[];
  isRunningPipeline: boolean;
  isRunningResearch: boolean;
  isGeneratingBrief: boolean;
  isGeneratingDraft: boolean;
  isReviewingDraftId: string | null;
  isSendingDraftId: string | null;
  onRunPipeline: () => void;
  onRunResearch: () => void;
  onGenerateBrief: () => void;
  onGenerateDraft: () => void;
  onReviewDraft: (draftId: string, approved: boolean) => void;
  onSendDraft: (draftId: string) => void;
  onRefresh: () => void;
}

export function LeadContextPanel({
  lead,
  research,
  brief,
  drafts,
  logs,
  pipelineRuns,
  latestTask,
  inboundMessages,
  inboundThreads,
  isRunningPipeline,
  isRunningResearch,
  isGeneratingBrief,
  isGeneratingDraft,
  isReviewingDraftId,
  isSendingDraftId,
  onRunPipeline,
  onRunResearch,
  onGenerateBrief,
  onGenerateDraft,
  onReviewDraft,
  onSendDraft,
  onRefresh,
}: LeadContextPanelProps) {
  return (
    <div className="space-y-6 lg:col-span-2">
      <LeadAnalysisSection
        lead={lead}
        isRunningPipeline={isRunningPipeline}
        onRunPipeline={onRunPipeline}
      />

      <LeadDossierSection
        research={research}
        isRunningResearch={isRunningResearch}
        onRunResearch={onRunResearch}
      />

      <LeadBriefSection
        brief={brief}
        isGeneratingBrief={isGeneratingBrief}
        onGenerateBrief={onGenerateBrief}
      />

      <LeadOutreachSection
        lead={lead}
        drafts={drafts}
        isGeneratingDraft={isGeneratingDraft}
        isReviewingDraftId={isReviewingDraftId}
        isSendingDraftId={isSendingDraftId}
        onGenerateDraft={onGenerateDraft}
        onReviewDraft={onReviewDraft}
        onSendDraft={onSendDraft}
      />

      <AiDecisionsPanel
        leadId={String(lead.id)}
        pipelineRunId={pipelineRuns[0]?.id ?? null}
      />

      <LeadPipelineSection
        pipelineRuns={pipelineRuns}
        latestTask={latestTask}
      />

      <LeadRepliesSection
        inboundMessages={inboundMessages}
        inboundThreads={inboundThreads}
        onRefresh={onRefresh}
      />

      <LeadTimelineSection
        logs={logs}
        notes={lead.notes}
      />
    </div>
  );
}

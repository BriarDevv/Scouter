"use client";

import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
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

import { LeadSummaryTab } from "./lead-summary-tab";
import { LeadOutreachSection } from "./lead-outreach-section";
import { LeadDossierSection } from "./lead-dossier-section";
import { LeadBriefSection } from "./lead-brief-section";
import { AiDecisionsPanel } from "./ai-decisions-panel";
import { LeadPipelineSection } from "./lead-pipeline-section";
import { LeadRepliesSection } from "./lead-replies-section";
import { LeadTimelineSection } from "./lead-timeline-section";

interface LeadTabsPanelProps {
  sidebar: React.ReactNode;
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

export function LeadTabsPanel({
  sidebar,
  lead, research, brief, drafts, logs, pipelineRuns, latestTask,
  inboundMessages, inboundThreads,
  isRunningPipeline, isRunningResearch, isGeneratingBrief, isGeneratingDraft,
  isReviewingDraftId, isSendingDraftId,
  onRunPipeline, onRunResearch, onGenerateBrief, onGenerateDraft,
  onReviewDraft, onSendDraft, onRefresh,
}: LeadTabsPanelProps) {
  return (
    <Tabs defaultValue={0}>
      <TabsList variant="line" className="w-full justify-start border-b border-border pb-px">
          <TabsTrigger value={0}>Resumen</TabsTrigger>
          <TabsTrigger value={1}>
            Outreach
            {drafts.length > 0 && (
              <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-data">{drafts.length}</span>
            )}
          </TabsTrigger>
          <TabsTrigger value={2}>Dossier</TabsTrigger>
          <TabsTrigger value={3}>IA</TabsTrigger>
          <TabsTrigger value={4}>
            Replies
            {inboundMessages.length > 0 && (
              <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-data">{inboundMessages.length}</span>
            )}
          </TabsTrigger>
          <TabsTrigger value={5}>Timeline</TabsTrigger>
        </TabsList>

      <div className="flex gap-6 pt-4">
        {sidebar}
        <div className="flex-1 min-w-0">

        <TabsContent value={0}>
          <LeadSummaryTab
            lead={lead}
            brief={brief}
            research={research}
            isRunningPipeline={isRunningPipeline}
            isRunningResearch={isRunningResearch}
            isGeneratingBrief={isGeneratingBrief}
            onRunPipeline={onRunPipeline}
            onRunResearch={onRunResearch}
            onGenerateBrief={onGenerateBrief}
          />
        </TabsContent>

        <TabsContent value={1}>
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
        </TabsContent>

        <TabsContent value={2}>
          <LeadDossierSection
            research={research}
            isRunningResearch={isRunningResearch}
            onRunResearch={onRunResearch}
          />
        </TabsContent>

        <TabsContent value={3} className="space-y-4">
          <LeadBriefSection
            brief={brief}
            isGeneratingBrief={isGeneratingBrief}
            onGenerateBrief={onGenerateBrief}
          />
          <AiDecisionsPanel
            leadId={String(lead.id)}
            pipelineRunId={pipelineRuns[0]?.id ?? null}
          />
          <LeadPipelineSection
            pipelineRuns={pipelineRuns}
            latestTask={latestTask}
          />
        </TabsContent>

        <TabsContent value={4}>
          <LeadRepliesSection
            inboundMessages={inboundMessages}
            inboundThreads={inboundThreads}
            onRefresh={onRefresh}
          />
        </TabsContent>

        <TabsContent value={5}>
          <LeadTimelineSection
            logs={logs}
            notes={lead.notes}
          />
        </TabsContent>

        </div>{/* flex-1 min-w-0 */}
      </div>{/* flex gap-6 */}
    </Tabs>
  );
}

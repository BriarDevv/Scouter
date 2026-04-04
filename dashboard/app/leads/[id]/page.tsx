"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  QualityBadge,
  StatusBadge,
} from "@/components/shared/status-badge";
import { RelativeTime } from "@/components/shared/relative-time";
import { Skeleton, SkeletonCard } from "@/components/shared/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import {
  generateDraft,
  generateBrief,
  getCommercialBrief,
  getDrafts,
  getInboundMessages,
  getInboundThreads,
  getLeadById,
  getLeadResearch,
  getOutreachLogs,
  getPipelineRuns,
  getTaskStatus,
  reviewDraft,
  reviewLeadWithIA,
  runFullPipeline,
  runResearch,
  updateLeadStatus,
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
import {
  ArrowLeft, RefreshCw, FileText, CheckCircle, ShieldCheck,
  Loader2,
} from "lucide-react";
import { sileo } from "sileo";

import { LeadContactCard } from "@/components/leads/lead-contact-card";
import { LeadAnalysisSection } from "@/components/leads/lead-analysis-section";
import { LeadDossierSection } from "@/components/leads/lead-dossier-section";
import { LeadBriefSection } from "@/components/leads/lead-brief-section";
import { LeadOutreachSection } from "@/components/leads/lead-outreach-section";
import { AiDecisionsPanel } from "@/components/leads/ai-decisions-panel";
import { LeadPipelineSection } from "@/components/leads/lead-pipeline-section";
import { LeadRepliesSection } from "@/components/leads/lead-replies-section";
import { LeadTimelineSection } from "@/components/leads/lead-timeline-section";

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
  const [isRunningPipeline, setIsRunningPipeline] = useState(false);
  const [isGeneratingDraft, setIsGeneratingDraft] = useState(false);
  const [isApprovingLead, setIsApprovingLead] = useState(false);
  const [isReviewingDraftId, setIsReviewingDraftId] = useState<string | null>(null);
  const [isReviewingLead, setIsReviewingLead] = useState(false);
  const [research, setResearch] = useState<LeadResearchReport | null>(null);
  const [brief, setBrief] = useState<CommercialBrief | null>(null);
  const [isRunningResearch, setIsRunningResearch] = useState(false);
  const [isGeneratingBrief, setIsGeneratingBrief] = useState(false);

  useEffect(() => {
    let active = true;

    async function loadLeadContext() {
      try {
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

        if (!active) return;

        setLead(nextLead);
        setDrafts(nextDrafts);
        setLogs(nextLogs);
        setPipelineRuns(nextPipelineRuns);
        setInboundMessages(nextInboundMessages);
        setInboundThreads(nextInboundThreads);
        setResearch(nextResearch);
        setBrief(nextBrief);
        setLatestTask(null);
        setIsMissing(false);
      } catch {
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
  }, [id]);

  async function refreshLeadContext() {
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
  }

  async function handleRunPipeline() {
    if (!lead) return;
    setIsRunningPipeline(true);
    try {
      await sileo.promise(
        (async () => {
          const task = await runFullPipeline(lead.id);
          const taskStatus = await getTaskStatus(task.task_id);
          setLatestTask(taskStatus);
          await refreshLeadContext();
        })(),
        {
          loading: { title: "Ejecutando pipeline..." },
          success: { title: "Pipeline completado" },
          error: (err: unknown) => ({
            title: "Error en pipeline",
            description: err instanceof Error ? err.message : "No se pudo ejecutar.",
          }),
        }
      );
    } finally {
      setIsRunningPipeline(false);
    }
  }

  async function handleGenerateDraft() {
    if (!lead) return;
    setIsGeneratingDraft(true);
    try {
      await sileo.promise(
        (async () => {
          await generateDraft(lead.id);
          await refreshLeadContext();
        })(),
        {
          loading: { title: "Generando borrador..." },
          success: { title: "Borrador generado" },
          error: (err: unknown) => ({
            title: "Error al generar borrador",
            description: err instanceof Error ? err.message : "No se pudo generar.",
          }),
        }
      );
    } finally {
      setIsGeneratingDraft(false);
    }
  }

  async function handleApproveLead() {
    if (!lead) return;
    setIsApprovingLead(true);
    try {
      await sileo.promise(
        (async () => {
          await updateLeadStatus(lead.id, "approved");
          await refreshLeadContext();
        })(),
        {
          loading: { title: "Aprobando lead..." },
          success: { title: "Lead aprobado" },
          error: (err: unknown) => ({
            title: "Error al aprobar",
            description: err instanceof Error ? err.message : "No se pudo aprobar.",
          }),
        }
      );
    } finally {
      setIsApprovingLead(false);
    }
  }

  async function handleReviewDraft(draftId: string, approved: boolean) {
    setIsReviewingDraftId(draftId);
    try {
      await sileo.promise(
        (async () => {
          await reviewDraft(draftId, approved);
          await refreshLeadContext();
        })(),
        {
          loading: { title: approved ? "Aprobando draft..." : "Rechazando draft..." },
          success: { title: approved ? "Draft aprobado" : "Draft rechazado" },
          error: (err: unknown) => ({
            title: "Error al revisar draft",
            description: err instanceof Error ? err.message : "No se pudo revisar.",
          }),
        }
      );
    } finally {
      setIsReviewingDraftId(null);
    }
  }

  async function handleRunResearch() {
    if (!lead) return;
    setIsRunningResearch(true);
    try {
      await sileo.promise(
        (async () => {
          const res = await runResearch(lead.id);
          setResearch(res);
        })(),
        {
          loading: { title: "Investigando lead..." },
          success: { title: "Investigacion completada" },
          error: (err: unknown) => ({
            title: "Error en investigacion",
            description: err instanceof Error ? err.message : "No se pudo investigar.",
          }),
        }
      );
    } finally {
      setIsRunningResearch(false);
    }
  }

  async function handleGenerateBrief() {
    if (!lead) return;
    setIsGeneratingBrief(true);
    try {
      await sileo.promise(
        (async () => {
          const res = await generateBrief(lead.id);
          setBrief(res);
        })(),
        {
          loading: { title: "Generando brief comercial..." },
          success: { title: "Brief generado" },
          error: (err: unknown) => ({
            title: "Error al generar brief",
            description: err instanceof Error ? err.message : "No se pudo generar.",
          }),
        }
      );
    } finally {
      setIsGeneratingBrief(false);
    }
  }

  async function handleReviewLead() {
    if (!lead) return;
    setIsReviewingLead(true);
    try {
      await sileo.promise(
        (async () => {
          await reviewLeadWithIA(lead.id);
          await refreshLeadContext();
        })(),
        {
          loading: { title: "Reviewer IA analizando..." },
          success: { title: "Análisis del Reviewer completado" },
          error: (err: unknown) => ({
            title: "Error en Reviewer IA",
            description: err instanceof Error ? err.message : "No se pudo analizar.",
          }),
        }
      );
    } finally {
      setIsReviewingLead(false);
    }
  }

  // Loading skeleton
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
          {/* Back button */}
          <Link href="/leads">
        <Button variant="ghost" size="sm" className="gap-1.5 rounded-xl">
          <ArrowLeft className="h-4 w-4" /> Volver a leads
        </Button>
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-foreground font-heading">{lead.business_name}</h1>
            <StatusBadge status={lead.status} />
            <QualityBadge quality={lead.quality} />
          </div>
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            {lead.industry && <span>{lead.industry}</span>}
            {lead.city && <span>{lead.city}{lead.zone ? `, ${lead.zone}` : ""}</span>}
            <span>
              Creado <RelativeTime date={lead.created_at} />
            </span>
          </div>
        </div>

        {/* Actions with tooltips */}
        <div className="flex items-center gap-2">
          <Tooltip>
            <TooltipTrigger
              render={
                <Button
                  variant="outline"
                  size="sm"
                  className="rounded-xl gap-1.5"
                  onClick={() => void handleRunPipeline()}
                  disabled={isRunningPipeline}
                />
              }
            >
              {isRunningPipeline ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
              Pipeline
            </TooltipTrigger>
            <TooltipContent>Ejecutar enrichment, scoring y análisis IA</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger
              render={
                <Button
                  variant="outline"
                  size="sm"
                  className="rounded-xl gap-1.5 text-amber-700 border-amber-200 hover:bg-amber-50 dark:hover:bg-amber-950/20"
                  onClick={() => void handleReviewLead()}
                  disabled={isReviewingLead}
                />
              }
            >
              {isReviewingLead ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ShieldCheck className="h-3.5 w-3.5" />}
              Reviewer
            </TooltipTrigger>
            <TooltipContent>Analizar con Reviewer IA (27B)</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger
              render={
                <Button
                  variant="outline"
                  size="sm"
                  className="rounded-xl gap-1.5"
                  onClick={() => void handleGenerateDraft()}
                  disabled={isGeneratingDraft}
                />
              }
            >
              {isGeneratingDraft ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileText className="h-3.5 w-3.5" />}
              Generar Draft
            </TooltipTrigger>
            <TooltipContent>Generar borrador de email con IA</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger
              render={
                <Button
                  variant="outline"
                  size="sm"
                  className="rounded-xl gap-1.5 text-emerald-700 border-emerald-200 hover:bg-emerald-50 dark:hover:bg-emerald-950/20"
                  onClick={() => void handleApproveLead()}
                  disabled={isApprovingLead}
                />
              }
            >
              {isApprovingLead ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle className="h-3.5 w-3.5" />}
              Aprobar
            </TooltipTrigger>
            <TooltipContent>Aprobar lead para outreach</TooltipContent>
          </Tooltip>
        </div>
      </div>

      {/* Main grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left column: Info + Score + Signals */}
        <LeadContactCard
          lead={lead}
          isRunningPipeline={isRunningPipeline}
          onRunPipeline={() => void handleRunPipeline()}
        />

        {/* Right column: Collapsible sections */}
        <div className="space-y-6 lg:col-span-2">
          <LeadAnalysisSection
            lead={lead}
            isRunningPipeline={isRunningPipeline}
            onRunPipeline={() => void handleRunPipeline()}
          />

          <LeadDossierSection
            research={research}
            isRunningResearch={isRunningResearch}
            onRunResearch={() => void handleRunResearch()}
          />

          <LeadBriefSection
            brief={brief}
            isGeneratingBrief={isGeneratingBrief}
            onGenerateBrief={() => void handleGenerateBrief()}
          />

          <LeadOutreachSection
            drafts={drafts}
            isGeneratingDraft={isGeneratingDraft}
            isReviewingDraftId={isReviewingDraftId}
            onGenerateDraft={() => void handleGenerateDraft()}
            onReviewDraft={(draftId, approved) => void handleReviewDraft(draftId, approved)}
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
            onRefresh={() => void refreshLeadContext()}
          />

          <LeadTimelineSection
            logs={logs}
            notes={lead.notes}
          />
        </div>
      </div>
        </div>
      </div>
    </div>
  );
}

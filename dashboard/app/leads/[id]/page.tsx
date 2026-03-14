"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  InboundClassificationStatusBadge,
  InboundReplyLabelBadge,
  QualityBadge,
  ScoreBadge,
  StatusBadge,
} from "@/components/shared/status-badge";
import { INBOUND_MATCH_VIA_LABELS } from "@/lib/constants";
import { SIGNAL_CONFIG } from "@/lib/constants";
import { RelativeTime } from "@/components/shared/relative-time";
import { ReplyDraftPanel } from "@/components/shared/reply-draft-panel";
import { CollapsibleSection } from "@/components/shared/collapsible-section";
import { Skeleton, SkeletonCard } from "@/components/shared/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import { formatDateTime, extractDomain } from "@/lib/formatters";
import { MOCK_LEADS, MOCK_DRAFTS, MOCK_LOGS } from "@/data/mock";
import {
  generateDraft,
  getDrafts,
  getInboundMessages,
  getInboundThreads,
  getLeadById,
  getOutreachLogs,
  getPipelineRuns,
  getTaskStatus,
  reviewDraft,
  runFullPipeline,
  updateLeadStatus,
} from "@/lib/api/client";
import type {
  EmailThreadSummary,
  InboundMessage,
  Lead,
  LeadSignal,
  PipelineRunSummary,
  TaskStatusRecord,
} from "@/types";
import {
  ArrowLeft, Globe, Instagram, Mail, Phone, MapPin, Building2,
  RefreshCw, FileText, CheckCircle, XCircle, Sparkles, Clock,
  MessageSquare, GitBranch, StickyNote, Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { sileo } from "sileo";

function InfoRow({ icon: Icon, label, value, href }: { icon: typeof Globe; label: string; value: string | null; href?: string }) {
  if (!value) return null;
  return (
    <div className="flex items-center gap-3 py-2">
      <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
      <span className="text-sm text-muted-foreground w-24 shrink-0">{label}</span>
      {href ? (
        <a href={href} target="_blank" rel="noopener noreferrer" className="text-sm text-violet-600 dark:text-violet-400 hover:underline truncate font-data">
          {value}
        </a>
      ) : (
        <span className="text-sm text-foreground truncate font-data">{value}</span>
      )}
    </div>
  );
}

function SignalsList({ signals, onRunPipeline, isRunning }: { signals: LeadSignal[]; onRunPipeline: () => void; isRunning: boolean }) {
  return (
    <div className="space-y-2">
      {signals.map((s) => {
        const config = SIGNAL_CONFIG[s.signal_type];
        return (
          <div
            key={s.id}
            className={cn(
              "flex items-center gap-3 rounded-xl px-3 py-2 text-sm",
              config?.severity === "positive"
                ? "bg-emerald-50/60 dark:bg-emerald-950/20"
                : "bg-muted"
            )}
          >
            <span className="text-base">{config?.emoji || "?"}</span>
            <div>
              <span className="font-medium text-foreground/80">{config?.label || s.signal_type}</span>
              {s.detail && <span className="text-muted-foreground"> — {s.detail}</span>}
            </div>
          </div>
        );
      })}
      {signals.length === 0 && (
        <EmptyState
          icon={Sparkles}
          title="Sin señales detectadas"
          description="Ejecutá el pipeline para detectar señales."
          className="py-6"
        >
          <Button
            variant="outline"
            size="sm"
            className="rounded-xl gap-1.5"
            onClick={onRunPipeline}
            disabled={isRunning}
          >
            {isRunning ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            Ejecutar Pipeline
          </Button>
        </EmptyState>
      )}
    </div>
  );
}

function LeadDetailSkeleton() {
  return (
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
  );
}

export default function LeadDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [lead, setLead] = useState<Lead | null>(MOCK_LEADS.find((item) => item.id === id) ?? null);
  const [drafts, setDrafts] = useState(MOCK_DRAFTS.filter((draft) => draft.lead_id === id));
  const [logs, setLogs] = useState(MOCK_LOGS.filter((log) => log.lead_id === id));
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

  useEffect(() => {
    let active = true;

    async function loadLeadContext() {
      try {
        const [nextLead, nextDrafts, nextLogs, nextPipelineRuns, nextInboundMessages, nextInboundThreads] = await Promise.all([
          getLeadById(id),
          getDrafts({ lead_id: id }),
          getOutreachLogs({ lead_id: id, limit: 20 }),
          getPipelineRuns({ lead_id: id, limit: 5 }),
          getInboundMessages({ lead_id: id, limit: 20 }).catch(() => []),
          getInboundThreads({ lead_id: id, limit: 10 }).catch(() => []),
        ]);

        if (!active) return;

        setLead(nextLead);
        setDrafts(nextDrafts);
        setLogs(nextLogs);
        setPipelineRuns(nextPipelineRuns);
        setInboundMessages(nextInboundMessages);
        setInboundThreads(nextInboundThreads);
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
    const [nextLead, nextDrafts, nextLogs, nextPipelineRuns, nextInboundMessages, nextInboundThreads] = await Promise.all([
      getLeadById(id),
      getDrafts({ lead_id: id }),
      getOutreachLogs({ lead_id: id, limit: 20 }),
      getPipelineRuns({ lead_id: id, limit: 5 }),
      getInboundMessages({ lead_id: id, limit: 20 }).catch(() => []),
      getInboundThreads({ lead_id: id, limit: 10 }).catch(() => []),
    ]);
    setLead(nextLead);
    setDrafts(nextDrafts);
    setLogs(nextLogs);
    setPipelineRuns(nextPipelineRuns);
    setInboundMessages(nextInboundMessages);
    setInboundThreads(nextInboundThreads);
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

  // Loading skeleton
  if (isLoading && !lead) {
    return <LeadDetailSkeleton />;
  }

  if (!lead || isMissing) {
    return (
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
    );
  }

  const threadById = new Map(inboundThreads.map((thread) => [thread.id, thread]));
  const latestInboundMessage = inboundMessages[0] ?? null;

  return (
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
        <div className="space-y-6 lg:col-span-1">
          <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-foreground mb-3 font-heading">Datos de contacto</h3>
            <div className="divide-y divide-border/50">
              <InfoRow icon={Globe} label="Website" value={extractDomain(lead.website_url)} href={lead.website_url || undefined} />
              <InfoRow icon={Instagram} label="Instagram" value={lead.instagram_url ? "@" + lead.instagram_url.split("/").pop() : null} href={lead.instagram_url || undefined} />
              <InfoRow icon={Mail} label="Email" value={lead.email} href={lead.email ? `mailto:${lead.email}` : undefined} />
              <InfoRow icon={Phone} label="Teléfono" value={lead.phone} />
              <InfoRow icon={MapPin} label="Ubicación" value={lead.city ? `${lead.city}${lead.zone ? `, ${lead.zone}` : ""}` : null} />
              <InfoRow icon={Building2} label="Rubro" value={lead.industry} />
            </div>
          </div>

          <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-foreground mb-3 font-heading">Score</h3>
            <div className="flex items-center gap-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
                <span className="text-2xl font-bold text-foreground font-data">{lead.score !== null ? lead.score.toFixed(0) : "—"}</span>
              </div>
              <div>
                <ScoreBadge score={lead.score} />
                <p className="mt-1 text-xs text-muted-foreground">de 100 puntos posibles</p>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-foreground mb-3 font-heading">Señales Detectadas</h3>
            <SignalsList
              signals={lead.signals ?? []}
              onRunPipeline={() => void handleRunPipeline()}
              isRunning={isRunningPipeline}
            />
          </div>
        </div>

        {/* Right column: Collapsible sections */}
        <div className="space-y-6 lg:col-span-2">
          {/* LLM Summary — always open */}
          <CollapsibleSection
            title="Análisis IA"
            icon={Sparkles}
            defaultOpen
          >
            {lead.llm_summary ? (
              <div className="space-y-3">
                <p className="text-sm text-foreground/80 leading-relaxed">{lead.llm_summary}</p>
                {lead.llm_quality_assessment && (
                  <div className="rounded-xl bg-muted/60 p-3">
                    <p className="text-xs font-medium text-muted-foreground mb-1">Evaluación de calidad</p>
                    <p className="text-sm text-foreground/80">{lead.llm_quality_assessment}</p>
                  </div>
                )}
                {lead.llm_suggested_angle && (
                  <div className="rounded-xl bg-muted/60 p-3">
                    <p className="text-xs font-medium text-muted-foreground mb-1">Ángulo comercial sugerido</p>
                    <p className="text-sm text-foreground/80">{lead.llm_suggested_angle}</p>
                  </div>
                )}
              </div>
            ) : (
              <EmptyState
                icon={Sparkles}
                title="Análisis IA no disponible"
                description="Ejecutá el pipeline para generar el análisis con el modelo configurado en Ollama."
                className="py-6"
              >
                <Button
                  variant="outline"
                  size="sm"
                  className="rounded-xl gap-1.5"
                  onClick={() => void handleRunPipeline()}
                  disabled={isRunningPipeline}
                >
                  {isRunningPipeline ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                  Ejecutar Análisis
                </Button>
              </EmptyState>
            )}
          </CollapsibleSection>

          {/* Drafts — always open */}
          <CollapsibleSection
            title="Borradores de Outreach"
            icon={FileText}
            defaultOpen
            badge={
              drafts.length > 0 ? (
                <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">{drafts.length}</span>
              ) : undefined
            }
          >
            {drafts.length > 0 ? (
              <div className="space-y-3">
                {drafts.map((draft) => (
                  <div key={draft.id} className="rounded-xl border border-border p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-foreground">{draft.subject}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground font-data">
                          <RelativeTime date={draft.generated_at} />
                        </span>
                        <span className={cn(
                          "rounded-full px-2 py-0.5 text-xs font-medium",
                          draft.status === "pending_review" && "bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-300",
                          draft.status === "approved" && "bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300",
                          draft.status === "sent" && "bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300",
                          draft.status === "rejected" && "bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300",
                        )}>
                          {draft.status === "pending_review" ? "Pendiente" : draft.status === "approved" ? "Aprobado" : draft.status === "sent" ? "Enviado" : "Rechazado"}
                        </span>
                      </div>
                    </div>
                    <p className="text-sm text-muted-foreground whitespace-pre-line leading-relaxed">{draft.body}</p>
                    {draft.status === "pending_review" && (
                      <div className="mt-3 flex gap-2">
                        <Button
                          size="sm"
                          className="rounded-xl bg-emerald-600 text-white hover:bg-emerald-700 gap-1.5"
                          onClick={() => void handleReviewDraft(draft.id, true)}
                          disabled={isReviewingDraftId === draft.id}
                        >
                          {isReviewingDraftId === draft.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle className="h-3.5 w-3.5" />}
                          Aprobar
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="rounded-xl gap-1.5 text-red-600 border-red-200 hover:bg-red-50 dark:hover:bg-red-950/20"
                          onClick={() => void handleReviewDraft(draft.id, false)}
                          disabled={isReviewingDraftId === draft.id}
                        >
                          <XCircle className="h-3.5 w-3.5" /> Rechazar
                        </Button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                icon={FileText}
                title="Sin borradores"
                description="Generá un borrador de outreach para este lead."
                className="py-6"
              >
                <Button
                  variant="outline"
                  size="sm"
                  className="rounded-xl gap-1.5"
                  onClick={() => void handleGenerateDraft()}
                  disabled={isGeneratingDraft}
                >
                  {isGeneratingDraft ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileText className="h-3.5 w-3.5" />}
                  Generar Draft
                </Button>
              </EmptyState>
            )}
          </CollapsibleSection>

          {/* Pipeline Runs — collapsed by default */}
          <CollapsibleSection
            title="Pipeline Async"
            icon={GitBranch}
            defaultOpen={false}
            badge={
              latestTask?.task_id ? (
                <span className="text-xs text-muted-foreground font-data">task {latestTask.task_id.slice(0, 8)}</span>
              ) : undefined
            }
          >
            {latestTask && (
              <div className="mb-4 rounded-xl border border-violet-100 dark:border-violet-900/30 bg-violet-50/40 dark:bg-violet-950/20 p-3">
                <p className="text-xs font-medium text-violet-700 dark:text-violet-300">Última task</p>
                <p className="mt-1 text-sm text-foreground/80">
                  {latestTask.status} {latestTask.current_step ? `· ${latestTask.current_step}` : ""}
                </p>
                {latestTask.pipeline_run_id && (
                  <p className="mt-1 text-xs text-muted-foreground font-data">run {latestTask.pipeline_run_id.slice(0, 8)}</p>
                )}
              </div>
            )}
            {pipelineRuns.length > 0 ? (
              <div className="space-y-3">
                {pipelineRuns.map((run) => (
                  <div key={run.id} className="rounded-xl border border-border p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium text-foreground">
                          {run.status} {run.current_step ? `· ${run.current_step}` : ""}
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground font-data">
                          run {run.id.slice(0, 8)} · <RelativeTime date={run.updated_at} />
                        </p>
                      </div>
                      {run.root_task_id && (
                        <span className="text-xs text-muted-foreground font-data">{run.root_task_id.slice(0, 8)}</span>
                      )}
                    </div>
                    {run.error && <p className="mt-2 text-xs text-red-600">{run.error}</p>}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-6">Sin ejecuciones async registradas</p>
            )}
          </CollapsibleSection>

          {/* Inbound Replies — open by default */}
          <CollapsibleSection
            title="Replies del lead"
            subtitle="Inbound real vinculado por delivery/thread y clasificado por el executor."
            icon={MessageSquare}
            defaultOpen
            badge={
              <span className="rounded-full bg-muted px-2.5 py-1 text-xs text-muted-foreground">
                {inboundMessages.length} replies
              </span>
            }
          >
            {latestInboundMessage && (
              <div className="mb-4 space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <InboundClassificationStatusBadge status={latestInboundMessage.classification_status} />
                  <InboundReplyLabelBadge label={latestInboundMessage.classification_label} />
                </div>
                <div>
                  <p className="text-sm font-medium text-foreground">
                    Última reply: {latestInboundMessage.from_name || latestInboundMessage.from_email || "Remitente desconocido"}
                  </p>
                  <p className="text-xs text-muted-foreground font-data">
                    {latestInboundMessage.subject || "(sin asunto)"}
                  </p>
                </div>
                {latestInboundMessage.summary && (
                  <p className="text-sm text-foreground/80">{latestInboundMessage.summary}</p>
                )}
                {latestInboundMessage.next_action_suggestion && (
                  <p className="text-sm text-muted-foreground">
                    <span className="font-medium text-foreground/80">Siguiente paso:</span>{" "}
                    {latestInboundMessage.next_action_suggestion}
                  </p>
                )}
                <ReplyDraftPanel
                  messageId={latestInboundMessage.id}
                  draft={latestInboundMessage.reply_assistant_draft ?? null}
                  compact
                  onRefresh={refreshLeadContext}
                />
              </div>
            )}
            {inboundMessages.length > 0 ? (
              <div className="space-y-3">
                {inboundMessages.map((message) => {
                  const thread = message.thread_id ? threadById.get(message.thread_id) : undefined;
                  return (
                    <div key={message.id} className="rounded-xl border border-border p-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="space-y-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <InboundClassificationStatusBadge status={message.classification_status} />
                            <InboundReplyLabelBadge label={message.classification_label} />
                            {message.should_escalate_reviewer && (
                              <span className="inline-flex items-center rounded-full bg-fuchsia-50 dark:bg-fuchsia-950/30 px-2.5 py-0.5 text-xs font-medium text-fuchsia-700 dark:text-fuchsia-300">
                                Sugerir reviewer
                              </span>
                            )}
                          </div>
                          <div>
                            <p className="text-sm font-medium text-foreground">
                              {message.from_name || message.from_email || "Remitente desconocido"}
                            </p>
                            <p className="text-xs text-muted-foreground font-data">
                              {message.subject || "(sin asunto)"}
                            </p>
                          </div>
                        </div>
                        <div className="text-right text-xs text-muted-foreground font-data">
                          <div>{formatDateTime(message.received_at || message.created_at)}</div>
                          <div className="mt-1">
                            <RelativeTime date={message.received_at || message.created_at} />
                          </div>
                        </div>
                      </div>

                      {message.summary && (
                        <p className="mt-3 text-sm text-foreground/80">{message.summary}</p>
                      )}
                      {message.next_action_suggestion && (
                        <p className="mt-2 text-sm text-muted-foreground">
                          <span className="font-medium text-foreground/80">Siguiente paso:</span>{" "}
                          {message.next_action_suggestion}
                        </p>
                      )}
                      {message.classification_error && (
                        <p className="mt-2 text-sm text-rose-600">{message.classification_error}</p>
                      )}
                      {message.body_snippet && (
                        <p className="mt-3 border-l-2 border-muted-foreground/30 pl-3 text-sm text-muted-foreground">
                          {message.body_snippet}
                        </p>
                      )}

                      <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
                        {thread && (
                          <span>
                            {INBOUND_MATCH_VIA_LABELS[thread.matched_via] || thread.matched_via}
                            {thread.match_confidence !== null ? ` · ${thread.match_confidence.toFixed(2)}` : ""}
                            {" · "}
                            {thread.message_count} mensaje(s)
                          </span>
                        )}
                        {message.classification_model && (
                          <span className="font-data">
                            {message.classification_role} · {message.classification_model}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <EmptyState
                icon={MessageSquare}
                title="Sin replies inbound"
                description="Este lead todavía no tiene replies inbound vinculadas."
                className="py-6"
              />
            )}
          </CollapsibleSection>

          {/* Timeline — collapsed by default */}
          <CollapsibleSection
            title="Timeline"
            icon={Clock}
            defaultOpen={false}
            badge={
              logs.length > 0 ? (
                <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">{logs.length}</span>
              ) : undefined
            }
          >
            {logs.length > 0 ? (
              <div className="space-y-3">
                {logs.map((log) => (
                  <div key={log.id} className="flex items-start gap-3">
                    <div className="mt-0.5 h-2 w-2 rounded-full bg-muted-foreground/30 shrink-0" />
                    <div>
                      <p className="text-sm text-foreground/80">
                        <span className="font-medium capitalize">{log.action}</span>
                        {log.detail && <span className="text-muted-foreground"> — {log.detail}</span>}
                      </p>
                      <p className="text-xs text-muted-foreground flex items-center gap-1 font-data">
                        <Clock className="h-3 w-3" />
                        {formatDateTime(log.created_at)} · {log.actor}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-6">Sin actividad registrada</p>
            )}
          </CollapsibleSection>

          {/* Notes — open only if notes exist */}
          {lead.notes && (
            <CollapsibleSection
              title="Notas"
              icon={StickyNote}
              defaultOpen
            >
              <p className="text-sm text-muted-foreground">{lead.notes}</p>
            </CollapsibleSection>
          )}
        </div>
      </div>
    </div>
  );
}

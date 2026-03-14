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
} from "lucide-react";
import { cn } from "@/lib/utils";

function InfoRow({ icon: Icon, label, value, href }: { icon: typeof Globe; label: string; value: string | null; href?: string }) {
  if (!value) return null;
  return (
    <div className="flex items-center gap-3 py-2">
      <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
      <span className="text-sm text-muted-foreground w-24 shrink-0">{label}</span>
      {href ? (
        <a href={href} target="_blank" rel="noopener noreferrer" className="text-sm text-violet-600 hover:underline truncate font-data">
          {value}
        </a>
      ) : (
        <span className="text-sm text-foreground truncate font-data">{value}</span>
      )}
    </div>
  );
}

function SignalsList({ signals }: { signals: LeadSignal[] }) {
  return (
    <div className="space-y-2">
      {signals.map((s) => {
        const config = SIGNAL_CONFIG[s.signal_type];
        return (
          <div
            key={s.id}
            className={cn(
              "flex items-center gap-3 rounded-xl px-3 py-2 text-sm",
              config?.severity === "positive" ? "bg-emerald-50/60" : "bg-muted"
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
        <p className="text-sm text-muted-foreground py-4 text-center">Sin señales detectadas. Ejecutá el enrichment.</p>
      )}
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

        if (!active) {
          return;
        }

        setLead(nextLead);
        setDrafts(nextDrafts);
        setLogs(nextLogs);
        setPipelineRuns(nextPipelineRuns);
        setInboundMessages(nextInboundMessages);
        setInboundThreads(nextInboundThreads);
        setLatestTask(null);
        setIsMissing(false);
      } catch {
        if (!active) {
          return;
        }
        setLead(null);
        setDrafts([]);
        setLogs([]);
        setPipelineRuns([]);
        setInboundMessages([]);
        setInboundThreads([]);
        setLatestTask(null);
        setIsMissing(true);
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
    if (!lead) {
      return;
    }
    setIsRunningPipeline(true);
    try {
      const task = await runFullPipeline(lead.id);
      const taskStatus = await getTaskStatus(task.task_id);
      setLatestTask(taskStatus);
      await refreshLeadContext();
    } finally {
      setIsRunningPipeline(false);
    }
  }

  async function handleGenerateDraft() {
    if (!lead) {
      return;
    }
    setIsGeneratingDraft(true);
    try {
      await generateDraft(lead.id);
      await refreshLeadContext();
    } finally {
      setIsGeneratingDraft(false);
    }
  }

  async function handleApproveLead() {
    if (!lead) {
      return;
    }
    setIsApprovingLead(true);
    try {
      await updateLeadStatus(lead.id, "approved");
      await refreshLeadContext();
    } finally {
      setIsApprovingLead(false);
    }
  }



  async function handleReviewDraft(draftId: string, approved: boolean) {
    setIsReviewingDraftId(draftId);
    try {
      await reviewDraft(draftId, approved);
      await refreshLeadContext();
    } finally {
      setIsReviewingDraftId(null);
    }
  }

  if (!lead || isMissing) {
    return (
      <div className="space-y-6">
        <Link href="/leads" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground/80">
          <ArrowLeft className="h-4 w-4" /> Volver a leads
        </Link>
        <div className="rounded-2xl border border-border bg-card p-12 text-center">
          <p className="text-muted-foreground">Lead no encontrado</p>
        </div>
      </div>
    );
  }

  const threadById = new Map(inboundThreads.map((thread) => [thread.id, thread]));
  const latestInboundMessage = inboundMessages[0] ?? null;

  return (
    <div className="space-y-6">
      {/* Back + Header */}
      <Link href="/leads" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground/80">
        <ArrowLeft className="h-4 w-4" /> Volver a leads
      </Link>

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

        {/* Actions */}
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="rounded-xl gap-1.5"
            onClick={() => void handleRunPipeline()}
            disabled={isRunningPipeline}
          >
            <RefreshCw className="h-3.5 w-3.5" /> Pipeline
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="rounded-xl gap-1.5"
            onClick={() => void handleGenerateDraft()}
            disabled={isGeneratingDraft}
          >
            <FileText className="h-3.5 w-3.5" /> Generar Draft
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="rounded-xl gap-1.5 text-emerald-700 border-emerald-200 hover:bg-emerald-50"
            onClick={() => void handleApproveLead()}
            disabled={isApprovingLead}
          >
            <CheckCircle className="h-3.5 w-3.5" /> Aprobar
          </Button>
        </div>
      </div>

      {/* Main grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left column: Info + Signals */}
        <div className="space-y-6 lg:col-span-1">
          {/* Contact Info */}
          <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-foreground mb-3 font-heading">Datos de contacto</h3>
            <div className="divide-y divide-slate-50">
              <InfoRow icon={Globe} label="Website" value={extractDomain(lead.website_url)} href={lead.website_url || undefined} />
              <InfoRow icon={Instagram} label="Instagram" value={lead.instagram_url ? "@" + lead.instagram_url.split("/").pop() : null} href={lead.instagram_url || undefined} />
              <InfoRow icon={Mail} label="Email" value={lead.email} href={lead.email ? `mailto:${lead.email}` : undefined} />
              <InfoRow icon={Phone} label="Teléfono" value={lead.phone} />
              <InfoRow icon={MapPin} label="Ubicación" value={lead.city ? `${lead.city}${lead.zone ? `, ${lead.zone}` : ""}` : null} />
              <InfoRow icon={Building2} label="Rubro" value={lead.industry} />
            </div>
          </div>

          {/* Score */}
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

          {/* Signals */}
          <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-foreground mb-3 font-heading">Señales Detectadas</h3>
            <SignalsList signals={lead.signals ?? []} />
          </div>
        </div>

        {/* Right column: LLM Analysis + Drafts + Timeline */}
        <div className="space-y-6 lg:col-span-2">
          {/* LLM Summary */}
          {lead.llm_summary && (
            <div className="rounded-2xl border border-violet-100 bg-violet-50/30 p-5 shadow-sm">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="h-4 w-4 text-violet-600" />
                <h3 className="text-sm font-semibold text-violet-900 font-heading">Análisis IA</h3>
              </div>
              <p className="text-sm text-foreground/80 leading-relaxed">{lead.llm_summary}</p>

              {lead.llm_quality_assessment && (
                <div className="mt-4 rounded-xl bg-card/60 p-3">
                  <p className="text-xs font-medium text-muted-foreground mb-1">Evaluación de calidad</p>
                  <p className="text-sm text-foreground/80">{lead.llm_quality_assessment}</p>
                </div>
              )}

              {lead.llm_suggested_angle && (
                <div className="mt-3 rounded-xl bg-card/60 p-3">
                  <p className="text-xs font-medium text-muted-foreground mb-1">Ángulo comercial sugerido</p>
                  <p className="text-sm text-foreground/80">{lead.llm_suggested_angle}</p>
                </div>
              )}
            </div>
          )}

          {!lead.llm_summary && (
            <div className="rounded-2xl border border-border bg-card p-8 text-center shadow-sm">
              <Sparkles className="mx-auto h-8 w-8 text-muted-foreground/50" />
              <p className="mt-3 text-sm font-medium text-muted-foreground">Análisis IA no disponible</p>
              <p className="mt-1 text-xs text-muted-foreground">Ejecuta el pipeline para generar el analisis con el modelo configurado en Ollama</p>
              <Button variant="outline" size="sm" className="mt-4 rounded-xl gap-1.5">
                <RefreshCw className="h-3.5 w-3.5" /> Ejecutar Análisis
              </Button>
            </div>
          )}

          {/* Drafts */}
          <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-foreground mb-4 font-heading">Borradores de Outreach</h3>
            {drafts.length > 0 ? (
              <div className="space-y-3">
                {drafts.map((draft) => (
                  <div key={draft.id} className="rounded-xl border border-border p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-foreground">{draft.subject}</span>
                      <span className={cn(
                        "rounded-full px-2 py-0.5 text-xs font-medium",
                        draft.status === "pending_review" && "bg-amber-50 dark:bg-amber-950/30 text-amber-700",
                        draft.status === "approved" && "bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700",
                        draft.status === "sent" && "bg-blue-50 dark:bg-blue-950/30 text-blue-700",
                        draft.status === "rejected" && "bg-red-50 dark:bg-red-950/30 text-red-700",
                      )}>
                        {draft.status === "pending_review" ? "Pendiente" : draft.status === "approved" ? "Aprobado" : draft.status === "sent" ? "Enviado" : "Rechazado"}
                      </span>
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
                          <CheckCircle className="h-3.5 w-3.5" /> Aprobar
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="rounded-xl gap-1.5 text-red-600 border-red-200 hover:bg-red-50"
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
              <p className="text-sm text-muted-foreground text-center py-6">No hay borradores generados</p>
            )}
          </div>

          {/* Pipeline Runs */}
          <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
            <div className="flex items-center justify-between gap-3 mb-4">
              <h3 className="text-sm font-semibold text-foreground font-heading">Pipeline Async</h3>
              {latestTask?.task_id && (
                <span className="text-xs text-muted-foreground font-data">task {latestTask.task_id.slice(0, 8)}</span>
              )}
            </div>
            {latestTask && (
              <div className="mb-4 rounded-xl border border-violet-100 bg-violet-50/40 p-3">
                <p className="text-xs font-medium text-violet-700">Última task</p>
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
          </div>

          <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-foreground font-heading">Replies del lead</h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  Inbound real vinculado por delivery/thread y clasificado por el executor.
                </p>
              </div>
              <span className="rounded-full bg-muted px-2.5 py-1 text-xs text-muted-foreground">
                {inboundMessages.length} replies
              </span>
            </div>
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
                              <span className="inline-flex items-center rounded-full bg-fuchsia-50 dark:bg-fuchsia-950/30 px-2.5 py-0.5 text-xs font-medium text-fuchsia-700">
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
                        <p className="mt-3 rounded-xl bg-muted px-3 py-2 text-sm text-muted-foreground">
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
              <p className="text-sm text-muted-foreground text-center py-6">
                Este lead todavía no tiene replies inbound vinculadas.
              </p>
            )}
          </div>

          {/* Timeline */}
          <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-foreground mb-4 font-heading">Timeline</h3>
            {logs.length > 0 ? (
              <div className="space-y-3">
                {logs.map((log) => (
                  <div key={log.id} className="flex items-start gap-3">
                    <div className="mt-0.5 h-2 w-2 rounded-full bg-slate-300 shrink-0" />
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
          </div>

          {/* Notes */}
          {lead.notes && (
            <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
              <h3 className="text-sm font-semibold text-foreground mb-2 font-heading">Notas</h3>
              <p className="text-sm text-muted-foreground">{lead.notes}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

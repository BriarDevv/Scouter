"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/shared/empty-state";
import { Skeleton, SkeletonStatCard, SkeletonCard } from "@/components/shared/skeleton";
import {
  DraftStatusBadge,
  InboundClassificationStatusBadge,
  InboundReplyLabelBadge,
} from "@/components/shared/status-badge";
import { RelativeTime } from "@/components/shared/relative-time";
import {
  getDraftDeliveries,
  getDrafts,
  getInboundMessages,
  getInboundThreads,
  getLeads,
  getOutreachLogs,
  reviewDraft,
  sendOutreachDraft,
} from "@/lib/api/client";
import type {
  Lead,
  DraftStatus,
  EmailThreadSummary,
  InboundMessage,
  OutreachDelivery,
  OutreachDraft,
} from "@/types";
import { DRAFT_STATUS_CONFIG, INBOUND_MATCH_VIA_LABELS } from "@/lib/constants";
import {
  Mail, CheckCircle, XCircle, Loader2, FileText, Send,
} from "lucide-react";
import { cn } from "@/lib/utils";
import Link from "next/link";
import { sileo } from "sileo";

const FILTER_OPTIONS: (DraftStatus | "all")[] = ["all", "pending_review", "approved", "sent", "rejected"];

export default function OutreachPage() {
  const [filter, setFilter] = useState<DraftStatus | "all">("all");
  const [selectedDraft, setSelectedDraft] = useState<OutreachDraft | null>(null);
  const [drafts, setDrafts] = useState<OutreachDraft[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [inboundMessages, setInboundMessages] = useState<InboundMessage[]>([]);
  const [inboundThreads, setInboundThreads] = useState<EmailThreadSummary[]>([]);
  const [selectedDeliveries, setSelectedDeliveries] = useState<OutreachDelivery[]>([]);
  const [mailError, setMailError] = useState<string | null>(null);
  const [isReviewingDraftId, setIsReviewingDraftId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function loadOutreachData() {
      const [nextDrafts, nextLeads, nextInboundMessages, nextInboundThreads] = await Promise.all([
        getDrafts(),
        getLeads({ page: 1, page_size: 200 }),
        getInboundMessages({ limit: 100 }).catch(() => null),
        getInboundThreads({ limit: 50 }).catch(() => null),
      ]);

      if (!active) return;

      setDrafts(nextDrafts);
      setLeads(nextLeads.items);
      if (nextInboundMessages && nextInboundThreads) {
        setInboundMessages(nextInboundMessages);
        setInboundThreads(nextInboundThreads);
        setMailError(null);
      } else {
        setInboundMessages([]);
        setInboundThreads([]);
        setMailError("No se pudo cargar el contexto de replies inbound.");
      }
      setSelectedDraft((current) =>
        current ? nextDrafts.find((draft) => draft.id === current.id) ?? null : nextDrafts[0] ?? null
      );
      setLoading(false);
    }

    void loadOutreachData();

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;

    async function loadSelectedDraftDeliveries() {
      if (!selectedDraft) {
        setSelectedDeliveries([]);
        return;
      }

      try {
        const deliveries = await getDraftDeliveries(selectedDraft.id);
        if (!active) return;
        setSelectedDeliveries(deliveries);
      } catch {
        if (!active) return;
        setSelectedDeliveries([]);
      }
    }

    void loadSelectedDraftDeliveries();

    return () => {
      active = false;
    };
  }, [selectedDraft]);

  const filteredDrafts = filter === "all"
    ? drafts
    : drafts.filter((d) => d.status === filter);
  const selectedReplies = selectedDraft
    ? inboundMessages.filter((message) => message.draft_id === selectedDraft.id)
    : [];
  const selectedThreads = selectedDraft
    ? inboundThreads.filter((thread) => thread.draft_id === selectedDraft.id)
    : [];

  // Tab counts
  const countByStatus = (status: DraftStatus) => drafts.filter((d) => d.status === status).length;

  async function handleReview(draftId: string, approved: boolean) {
    setIsReviewingDraftId(draftId);
    try {
      await sileo.promise(
        (async () => {
          const updated = await reviewDraft(draftId, approved);
          setDrafts((current) =>
            current.map((draft) => (draft.id === draftId ? { ...draft, ...updated } : draft))
          );
        })(),
        {
          loading: { title: approved ? "Aprobando draft..." : "Rechazando draft..." },
          success: { title: approved ? "Draft aprobado" : "Draft rechazado" },
          error: (err: unknown) => ({
            title: "Error al revisar",
            description: err instanceof Error ? err.message : "No se pudo revisar el draft.",
          }),
        }
      );
    } finally {
      setIsReviewingDraftId(null);
    }
  }

  const [isSendingDraftId, setIsSendingDraftId] = useState<string | null>(null);

  async function handleSend(draftId: string) {
    setIsSendingDraftId(draftId);
    try {
      await sileo.promise(
        (async () => {
          await sendOutreachDraft(draftId);
          setDrafts((current) =>
            current.map((draft) => (draft.id === draftId ? { ...draft, status: "sent" as DraftStatus } : draft))
          );
        })(),
        {
          loading: { title: "Enviando mail..." },
          success: { title: "Mail enviado" },
          error: (err: unknown) => ({
            title: "Error al enviar",
            description: err instanceof Error ? err.message : "No se pudo enviar el mail.",
          }),
        }
      );
    } finally {
      setIsSendingDraftId(null);
    }
  }

  if (loading) {
    return (
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[1400px] px-8 py-8">
          <div className="space-y-6">
            <PageHeader title="Outreach" description="Gestión de borradores y actividad comercial" />
            <div className="grid gap-6 lg:grid-cols-3">
              <div className="lg:col-span-2 space-y-4">
                <Skeleton className="h-9 w-full max-w-md" />
                {Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} />)}
              </div>
              <div>
                <SkeletonCard className="h-64" />
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8">
        <div className="space-y-6">
          <PageHeader
            title="Outreach"
            description="Gestión de borradores y actividad comercial"
          />

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left: Drafts list */}
        <div className="lg:col-span-2 space-y-4">
          {/* Tab-style filters with counts */}
          <div className="flex items-center gap-0 border-b border-border">
            {FILTER_OPTIONS.map((s) => {
              const isActive = filter === s;
              const count = s === "all" ? drafts.length : countByStatus(s);
              return (
                <button
                  key={s}
                  onClick={() => setFilter(s)}
                  className={cn(
                    "relative px-3 py-2.5 text-sm font-medium transition-colors",
                    isActive
                      ? "text-violet-700 dark:text-violet-300"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  {s === "all" ? "Todos" : DRAFT_STATUS_CONFIG[s].label}
                  <span className={cn(
                    "ml-1.5 rounded-full px-1.5 py-0.5 text-xs",
                    isActive ? "bg-violet-100 dark:bg-violet-950/40 text-violet-700 dark:text-violet-300" : "bg-muted text-muted-foreground"
                  )}>
                    {count}
                  </span>
                  {isActive && (
                    <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-violet-600 dark:bg-violet-400 rounded-full" />
                  )}
                </button>
              );
            })}
          </div>

          {/* Drafts */}
          <div className="space-y-3">
            {filteredDrafts.map((draft) => {
              const lead = draft.lead ?? leads.find((item) => item.id === draft.lead_id);
              const isSelected = selectedDraft?.id === draft.id;
              return (
                <div
                  key={draft.id}
                  onClick={() => setSelectedDraft(draft)}
                  className={cn(
                    "cursor-pointer rounded-2xl border bg-card p-5 shadow-sm transition-all hover:shadow-md",
                    isSelected
                      ? "border-l-4 border-l-violet-500 border-violet-200 dark:border-violet-800"
                      : "border-border"
                  )}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-1.5">
                        <DraftStatusBadge status={draft.status} />
                        {draft.channel === "whatsapp" ? (
                          <span className="inline-flex items-center rounded-md bg-emerald-50 dark:bg-emerald-950/40 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700 dark:text-emerald-300">
                            WA
                          </span>
                        ) : (
                          <span className="inline-flex items-center rounded-md bg-blue-50 dark:bg-blue-950/40 px-1.5 py-0.5 text-[10px] font-medium text-blue-700 dark:text-blue-300">
                            Email
                          </span>
                        )}
                        {lead && (
                          <Link href={`/leads/${lead.id}`} className="text-xs text-muted-foreground hover:text-violet-600 transition-colors">
                            {lead.business_name}
                          </Link>
                        )}
                      </div>
                      <h4 className="text-sm font-medium text-foreground font-heading">{draft.subject}</h4>
                      <p className="mt-1 text-sm text-muted-foreground line-clamp-2">{draft.body}</p>
                    </div>
                    <RelativeTime
                      date={draft.generated_at}
                      className="shrink-0 text-xs text-muted-foreground font-data"
                    />
                  </div>

                  {draft.status === "pending_review" && (
                    <div className="mt-3 flex gap-2 border-t border-border/50 pt-3">
                      <Button
                        size="sm"
                        className="rounded-xl bg-emerald-600 text-white hover:bg-emerald-700 gap-1.5 h-8"
                        onClick={(e) => { e.stopPropagation(); void handleReview(draft.id, true); }}
                        disabled={isReviewingDraftId === draft.id}
                      >
                        {isReviewingDraftId === draft.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle className="h-3.5 w-3.5" />}
                        Aprobar
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="rounded-xl gap-1.5 h-8 text-red-600 border-red-200 hover:bg-red-50 dark:hover:bg-red-950/20"
                        onClick={(e) => { e.stopPropagation(); void handleReview(draft.id, false); }}
                        disabled={isReviewingDraftId === draft.id}
                      >
                        <XCircle className="h-3.5 w-3.5" /> Rechazar
                      </Button>
                    </div>
                  )}

                  {draft.status === "approved" && (
                    <div className="mt-3 flex gap-2 border-t border-border/50 pt-3">
                      <Button
                        size="sm"
                        className="rounded-xl bg-blue-600 text-white hover:bg-blue-700 gap-1.5 h-8"
                        onClick={(e) => { e.stopPropagation(); void handleSend(draft.id); }}
                        disabled={isSendingDraftId === draft.id}
                      >
                        {isSendingDraftId === draft.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                        Enviar Mail
                      </Button>
                    </div>
                  )}
                </div>
              );
            })}

            {filteredDrafts.length === 0 && (
              <EmptyState
                icon={Mail}
                title="Sin drafts"
                description="No hay drafts con este filtro."
              />
            )}
          </div>
        </div>

        {/* Right: Thread details only */}
        <div>
          <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-foreground font-heading">Hilo del draft</h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  Delivery real y replies inbound vinculadas al borrador seleccionado.
                </p>
              </div>
              {selectedDraft && <DraftStatusBadge status={selectedDraft.status} />}
            </div>

            {selectedDraft ? (
              <div className="mt-4 space-y-4">
                <div className="rounded-xl border border-border bg-muted/60 p-3">
                  {selectedDraft.channel !== "whatsapp" && (
                    <p className="text-sm font-medium text-foreground">{selectedDraft.subject}</p>
                  )}
                  <p className={cn(
                    "text-xs text-muted-foreground line-clamp-3",
                    selectedDraft.channel !== "whatsapp" && "mt-1"
                  )}>{selectedDraft.body}</p>
                  <p className="mt-2 text-xs text-muted-foreground font-data">
                    Generado <RelativeTime date={selectedDraft.generated_at} />
                  </p>
                </div>

                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Deliveries</p>
                  {selectedDeliveries.length > 0 ? (
                    <div className="mt-2 space-y-2">
                      {selectedDeliveries.map((delivery) => (
                        <div key={delivery.id} className="rounded-xl border border-border px-3 py-3">
                          <div className="flex items-center justify-between gap-3">
                            <span className={cn(
                              "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
                              delivery.status === "sent" && "bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300",
                              delivery.status === "sending" && "bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-300",
                              delivery.status === "failed" && "bg-rose-50 dark:bg-rose-950/30 text-rose-700 dark:text-rose-300"
                            )}>
                              {delivery.status}
                            </span>
                            <span className="text-xs text-muted-foreground font-data">
                              {delivery.sent_at ? <RelativeTime date={delivery.sent_at} /> : "Sin envío"}
                            </span>
                          </div>
                          <p className="mt-2 text-sm text-foreground/80">{delivery.recipient_email}</p>
                          {delivery.error && <p className="mt-1 text-xs text-rose-600">{delivery.error}</p>}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-2 text-sm text-muted-foreground">Este draft todavía no tiene deliveries registradas.</p>
                  )}
                </div>

                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Replies vinculadas</p>
                  {mailError && (
                    <p className="mt-2 text-xs text-rose-600">{mailError}</p>
                  )}
                  {selectedReplies.length > 0 ? (
                    <div className="mt-2 space-y-2">
                      {selectedReplies.map((message) => {
                        const thread = selectedThreads.find((item) => item.id === message.thread_id);
                        return (
                          <div key={message.id} className="rounded-xl border border-border px-3 py-3">
                            <div className="flex flex-wrap items-center gap-2">
                              <InboundClassificationStatusBadge status={message.classification_status} />
                              <InboundReplyLabelBadge label={message.classification_label} />
                              {message.should_escalate_reviewer && (
                                <span className="inline-flex items-center rounded-full bg-fuchsia-50 dark:bg-fuchsia-950/30 px-2.5 py-0.5 text-xs font-medium text-fuchsia-700 dark:text-fuchsia-300">
                                  Sugerir reviewer
                                </span>
                              )}
                            </div>
                            <p className="mt-2 text-sm text-foreground">
                              {message.from_name || message.from_email || "Reply sin remitente"}
                            </p>
                            {message.summary && <p className="mt-1 text-sm text-foreground/80">{message.summary}</p>}
                            {message.next_action_suggestion && (
                              <p className="mt-1 text-xs text-muted-foreground">
                                Siguiente paso: {message.next_action_suggestion}
                              </p>
                            )}
                            <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted-foreground font-data">
                              <span>
                                <RelativeTime date={message.received_at || message.created_at} />
                              </span>
                              {thread && (
                                <span>
                                  {INBOUND_MATCH_VIA_LABELS[thread.matched_via] || thread.matched_via}
                                  {thread.match_confidence !== null ? ` · ${thread.match_confidence.toFixed(2)}` : ""}
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <p className="mt-2 text-sm text-muted-foreground">Todavía no hay replies vinculadas a este draft.</p>
                  )}
                </div>
              </div>
            ) : (
              <EmptyState
                icon={FileText}
                title="Seleccioná un draft"
                description="Elegí un borrador de la lista para ver su hilo de delivery y replies."
                className="py-8 mt-4"
              />
            )}
          </div>
        </div>
      </div>
        </div>
      </div>
    </div>
  );
}

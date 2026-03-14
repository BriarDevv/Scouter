"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import {
  DraftStatusBadge,
  InboundClassificationStatusBadge,
  InboundReplyLabelBadge,
  StatusBadge,
} from "@/components/shared/status-badge";
import { RelativeTime } from "@/components/shared/relative-time";
import { formatDate, truncate } from "@/lib/formatters";
import { MOCK_DRAFTS, MOCK_LOGS, MOCK_LEADS } from "@/data/mock";
import {
  getDraftDeliveries,
  getDrafts,
  getInboundMessages,
  getInboundThreads,
  getLeads,
  getOutreachLogs,
  reviewDraft,
} from "@/lib/api/client";
import type {
  DraftStatus,
  EmailThreadSummary,
  InboundMessage,
  OutreachDelivery,
  OutreachDraft,
  OutreachLog,
} from "@/types";
import { DRAFT_STATUS_CONFIG, INBOUND_MATCH_VIA_LABELS } from "@/lib/constants";
import {
  Mail, CheckCircle, XCircle, Send, Eye, MessageSquare,
  CalendarCheck, Trophy, FileText, Clock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import Link from "next/link";

const ACTION_CONFIG: Record<string, { icon: typeof FileText; label: string; color: string }> = {
  generated: { icon: FileText, label: "Draft generado", color: "text-muted-foreground" },
  approved: { icon: CheckCircle, label: "Aprobado", color: "text-emerald-600" },
  rejected: { icon: XCircle, label: "Rechazado", color: "text-red-500" },
  sent: { icon: Send, label: "Enviado", color: "text-blue-600" },
  opened: { icon: Eye, label: "Abierto", color: "text-amber-600" },
  replied: { icon: MessageSquare, label: "Respondió", color: "text-emerald-600" },
  meeting: { icon: CalendarCheck, label: "Reunión", color: "text-teal-600" },
  won: { icon: Trophy, label: "Ganado", color: "text-green-600" },
  lost: { icon: XCircle, label: "Perdido", color: "text-red-500" },
  reviewed: { icon: Eye, label: "Revisado", color: "text-indigo-600" },
};

const FILTER_OPTIONS: (DraftStatus | "all")[] = ["all", "pending_review", "approved", "sent", "rejected"];

export default function OutreachPage() {
  const [filter, setFilter] = useState<DraftStatus | "all">("all");
  const [selectedDraft, setSelectedDraft] = useState<OutreachDraft | null>(null);
  const [drafts, setDrafts] = useState(MOCK_DRAFTS);
  const [logs, setLogs] = useState(MOCK_LOGS);
  const [leads, setLeads] = useState(MOCK_LEADS);
  const [inboundMessages, setInboundMessages] = useState<InboundMessage[]>([]);
  const [inboundThreads, setInboundThreads] = useState<EmailThreadSummary[]>([]);
  const [selectedDeliveries, setSelectedDeliveries] = useState<OutreachDelivery[]>([]);
  const [mailError, setMailError] = useState<string | null>(null);
  const [isReviewingDraftId, setIsReviewingDraftId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadOutreachData() {
      const [nextDrafts, nextLogs, nextLeads, nextInboundMessages, nextInboundThreads] = await Promise.all([
        getDrafts(),
        getOutreachLogs({ limit: 50 }),
        getLeads({ page: 1, page_size: 200 }),
        getInboundMessages({ limit: 100 }).catch(() => null),
        getInboundThreads({ limit: 50 }).catch(() => null),
      ]);

      if (!active) {
        return;
      }

      setDrafts(nextDrafts);
      setLogs(nextLogs);
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
        if (!active) {
          return;
        }
        setSelectedDeliveries(deliveries);
      } catch {
        if (!active) {
          return;
        }
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

  async function handleReview(draftId: string, approved: boolean) {
    setIsReviewingDraftId(draftId);
    try {
      const updated = await reviewDraft(draftId, approved);
      setDrafts((current) =>
        current.map((draft) => (draft.id === draftId ? { ...draft, ...updated } : draft))
      );
      setLogs(await getOutreachLogs({ limit: 50 }));
    } finally {
      setIsReviewingDraftId(null);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Outreach"
        description="Gestión de borradores y actividad comercial"
      />

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left: Drafts list */}
        <div className="lg:col-span-2 space-y-4">
          {/* Filters */}
          <div className="flex items-center gap-1.5">
            {FILTER_OPTIONS.map((s) => (
              <button
                key={s}
                onClick={() => setFilter(s)}
                className={cn(
                  "rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors",
                  filter === s
                    ? "bg-violet-100 text-violet-700"
                    : "bg-card text-muted-foreground hover:bg-muted border border-border"
                )}
              >
                {s === "all" ? "Todos" : DRAFT_STATUS_CONFIG[s].label}
              </button>
            ))}
          </div>

          {/* Drafts */}
          <div className="space-y-3">
            {filteredDrafts.map((draft) => {
              const lead = draft.lead ?? leads.find((item) => item.id === draft.lead_id);
              return (
                <div
                  key={draft.id}
                  onClick={() => setSelectedDraft(draft)}
                  className={cn(
                    "cursor-pointer rounded-2xl border bg-card p-5 shadow-sm transition-all hover:shadow-md",
                    selectedDraft?.id === draft.id ? "border-violet-200 ring-1 ring-violet-100" : "border-border"
                  )}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-1.5">
                        <DraftStatusBadge status={draft.status} />
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
                        onClick={() => void handleReview(draft.id, true)}
                        disabled={isReviewingDraftId === draft.id}
                      >
                        <CheckCircle className="h-3.5 w-3.5" /> Aprobar
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="rounded-xl gap-1.5 h-8 text-red-600 border-red-200 hover:bg-red-50"
                        onClick={() => void handleReview(draft.id, false)}
                        disabled={isReviewingDraftId === draft.id}
                      >
                        <XCircle className="h-3.5 w-3.5" /> Rechazar
                      </Button>
                    </div>
                  )}
                </div>
              );
            })}

            {filteredDrafts.length === 0 && (
              <div className="rounded-2xl border border-border bg-card p-12 text-center">
                <Mail className="mx-auto h-8 w-8 text-muted-foreground/50" />
                <p className="mt-3 text-sm text-muted-foreground">No hay drafts con este filtro</p>
              </div>
            )}
          </div>
        </div>

        {/* Right: Thread + Activity */}
        <div className="space-y-4">
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
                  <p className="text-sm font-medium text-foreground">{selectedDraft.subject}</p>
                  <p className="mt-1 text-xs text-muted-foreground line-clamp-3">{selectedDraft.body}</p>
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
                              delivery.status === "sent" && "bg-blue-50 dark:bg-blue-950/30 text-blue-700",
                              delivery.status === "sending" && "bg-amber-50 dark:bg-amber-950/30 text-amber-700",
                              delivery.status === "failed" && "bg-rose-50 dark:bg-rose-950/30 text-rose-700"
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
                                <span className="inline-flex items-center rounded-full bg-fuchsia-50 dark:bg-fuchsia-950/30 px-2.5 py-0.5 text-xs font-medium text-fuchsia-700">
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
              <p className="mt-4 text-sm text-muted-foreground">Seleccioná un draft para ver su hilo.</p>
            )}
          </div>

          <h3 className="text-sm font-semibold text-foreground font-heading">Actividad Reciente</h3>

          <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
            <div className="space-y-1">
              {logs.map((log) => {
                const config = ACTION_CONFIG[log.action] || ACTION_CONFIG.generated;
                const Icon = config.icon;
                const lead = leads.find((item) => item.id === log.lead_id);

                return (
                  <div key={log.id} className="flex items-start gap-3 rounded-xl px-2 py-2.5 hover:bg-muted transition-colors">
                    <Icon className={cn("h-4 w-4 mt-0.5 shrink-0", config.color)} />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-foreground/80">
                        <span className="font-medium">{config.label}</span>
                        {lead && <span className="text-muted-foreground"> — {lead.business_name}</span>}
                      </p>
                      {log.detail && <p className="text-xs text-muted-foreground mt-0.5">{log.detail}</p>}
                      <p className="text-xs text-muted-foreground mt-0.5 flex items-center gap-1 font-data">
                        <Clock className="h-3 w-3" />
                        <RelativeTime date={log.created_at} />
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

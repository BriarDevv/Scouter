"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Inbox,
  LifeBuoy,
  MailSearch,
  MessagesSquare,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { RelativeTime } from "@/components/shared/relative-time";
import { StatCard } from "@/components/shared/stat-card";
import {
  InboundClassificationStatusBadge,
  InboundReplyLabelBadge,
} from "@/components/shared/status-badge";
import { sileo } from "sileo";
import { Button } from "@/components/ui/button";
import { ReplyDraftPanel } from "@/components/shared/reply-draft-panel";
import {
  getDrafts,
  getInboundMailStatus,
  getInboundMessages,
  getInboundThreads,
  getLeads,
  classifyInboundMessage,
  classifyPendingInboundMessages,
  syncInboundMail,
} from "@/lib/api/client";
import {
  INBOUND_MATCH_VIA_LABELS,
  POSITIVE_REPLY_LABELS,
} from "@/lib/constants";
import { formatDateTime } from "@/lib/formatters";
import type {
  EmailThreadSummary,
  InboundMailStatus,
  InboundMessage,
  Lead,
  OutreachDraft,
} from "@/types";

function safeDate(value: string | null | undefined) {
  return value ?? new Date(0).toISOString();
}

export default function ResponsesPage() {
  const [messages, setMessages] = useState<InboundMessage[]>([]);
  const [threads, setThreads] = useState<EmailThreadSummary[]>([]);
  const [status, setStatus] = useState<InboundMailStatus | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [drafts, setDrafts] = useState<OutreachDraft[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isClassifying, setIsClassifying] = useState(false);
  const [classifyingMessageId, setClassifyingMessageId] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "pending" | "classified" | "failed">("all");

  async function loadInboxData() {
    setLoading(true);
    setError(null);
    try {
      const [nextMessages, nextThreads, nextStatus, nextLeads, nextDrafts] = await Promise.all([
        getInboundMessages({ limit: 100 }),
        getInboundThreads({ limit: 50 }),
        getInboundMailStatus(),
        getLeads({ page: 1, page_size: 200 }),
        getDrafts(),
      ]);
      setMessages(nextMessages);
      setThreads(nextThreads);
      setStatus(nextStatus);
      setLeads(nextLeads.items);
      setDrafts(nextDrafts);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "No se pudo cargar el inbox.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadInboxData();
  }, []);

  const leadById = useMemo(
    () => new Map(leads.map((lead) => [lead.id, lead])),
    [leads]
  );
  const draftById = useMemo(
    () => new Map(drafts.map((draft) => [draft.id, draft])),
    [drafts]
  );
  const threadById = useMemo(
    () => new Map(threads.map((thread) => [thread.id, thread])),
    [threads]
  );

  const filteredMessages = useMemo(() => {
    if (filter === "all") {
      return messages;
    }
    return messages.filter((message) => message.classification_status === filter);
  }, [filter, messages]);

  const recentRepliesCount = messages.length;
  const repliedLeadsCount = new Set(messages.map((message) => message.lead_id).filter(Boolean)).size;
  const positiveRepliesCount = messages.filter(
    (message) => message.classification_label && POSITIVE_REPLY_LABELS.includes(message.classification_label)
  ).length;
  const quoteRepliesCount = messages.filter(
    (message) => message.classification_label === "asked_for_quote"
  ).length;
  const meetingRepliesCount = messages.filter(
    (message) => message.classification_label === "asked_for_meeting"
  ).length;
  const pendingCount = messages.filter((message) => message.classification_status === "pending").length;
  const escalatedCount = messages.filter((message) => message.should_escalate_reviewer).length;

  async function handleSync() {
    setIsSyncing(true);
    try {
      await syncInboundMail();
      await loadInboxData();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "No se pudo sincronizar el inbox.");
    } finally {
      setIsSyncing(false);
    }
  }

  async function handleClassifyPending() {
    setIsClassifying(true);
    try {
      await classifyPendingInboundMessages(25);
      await loadInboxData();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "No se pudieron clasificar los replies.");
    } finally {
      setIsClassifying(false);
    }
  }

  async function handleClassifyMessage(messageId: string) {
    setClassifyingMessageId(messageId);
    try {
      await classifyInboundMessage(messageId);
      await loadInboxData();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "No se pudo clasificar el reply.");
    } finally {
      setClassifyingMessageId(null);
    }
  }



  return (
    <div className="space-y-6">
      <PageHeader
        title="Respuestas"
        description="Inbox comercial grounded sobre inbound mail real, matching a deliveries y clasificación con executor."
      >
        <Button
          variant="outline"
          className="rounded-xl gap-1.5"
          onClick={() => void handleSync()}
          disabled={isSyncing}
        >
          <RefreshCw className="h-4 w-4" />
          {isSyncing ? "Sincronizando..." : "Sync inbox"}
        </Button>
        <Button
          variant="outline"
          className="rounded-xl gap-1.5"
          onClick={() => void handleClassifyPending()}
          disabled={isClassifying || pendingCount === 0}
        >
          <Sparkles className="h-4 w-4" />
          {isClassifying ? "Clasificando..." : "Clasificar pendientes"}
        </Button>
      </PageHeader>

      {error && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 dark:bg-rose-950/30 px-4 py-4 text-sm text-rose-700">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <p className="font-medium">No se pudo cargar el canal inbound</p>
              <p className="mt-1 text-rose-600">{error}</p>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 xl:grid-cols-6">
        <StatCard label="Replies recientes" value={recentRepliesCount} icon={Inbox} iconBg="bg-violet-50" iconColor="text-violet-600" />
        <StatCard label="Leads que respondieron" value={repliedLeadsCount} icon={MessagesSquare} iconBg="bg-emerald-50" iconColor="text-emerald-600" />
        <StatCard label="Replies positivas" value={positiveRepliesCount} icon={Sparkles} iconBg="bg-cyan-50" iconColor="text-cyan-600" />
        <StatCard label="Pidieron cotización" value={quoteRepliesCount} icon={MailSearch} iconBg="bg-blue-50" iconColor="text-blue-600" />
        <StatCard label="Pidieron reunión" value={meetingRepliesCount} icon={MessagesSquare} iconBg="bg-teal-50" iconColor="text-teal-600" />
        <StatCard label="Sugeridas a reviewer" value={escalatedCount} icon={LifeBuoy} iconBg="bg-fuchsia-50" iconColor="text-fuchsia-600" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.5fr,0.9fr]">
        <section className="rounded-2xl border border-border bg-card p-5 shadow-sm">
          <div className="mb-4 flex items-center justify-between gap-4">
            <div>
              <h2 className="font-heading text-base font-semibold text-foreground">Replies recientes</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Estado real del inbox inbound, con clasificación persistida y matching al hilo comercial.
              </p>
            </div>
            <div className="flex items-center gap-1.5">
              {(["all", "pending", "classified", "failed"] as const).map((value) => (
                <button
                  key={value}
                  onClick={() => setFilter(value)}
                  className={`rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors ${
                    filter === value
                      ? "bg-violet-100 text-violet-700"
                      : "border border-border bg-card text-muted-foreground hover:bg-muted"
                  }`}
                >
                  {value === "all" ? "Todos" : value === "pending" ? "Pendientes" : value === "classified" ? "Clasificados" : "Fallidos"}
                </button>
              ))}
            </div>
          </div>

          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, index) => (
                <div key={index} className="animate-pulse rounded-2xl border border-border p-4">
                  <div className="h-4 w-40 rounded bg-muted" />
                  <div className="mt-3 h-3 w-full rounded bg-muted" />
                  <div className="mt-2 h-3 w-2/3 rounded bg-muted" />
                </div>
              ))}
            </div>
          ) : filteredMessages.length === 0 ? (
            <EmptyState
              icon={Inbox}
              title="Sin replies para este filtro"
              description="Todavía no hay respuestas inbound que cumplan este criterio."
              className="py-10"
            />
          ) : (
            <div className="space-y-3">
              {filteredMessages.map((message) => {
                const lead = message.lead_id ? leadById.get(message.lead_id) : null;
                const outboundDraft = message.draft_id ? draftById.get(message.draft_id) : null;
                const thread = message.thread_id ? threadById.get(message.thread_id) : null;

                return (
                  <article key={message.id} className="rounded-2xl border border-border p-4">
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
                            {message.from_name || message.from_email || "Reply sin remitente"}
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

                    <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
                      {lead && (
                        <Link href={`/leads/${lead.id}`} className="text-violet-600 hover:underline">
                          {lead.business_name}
                        </Link>
                      )}
                      {outboundDraft && <span>Draft outbound: {outboundDraft.subject}</span>}
                      {thread && (
                        <span>
                          {INBOUND_MATCH_VIA_LABELS[thread.matched_via] || thread.matched_via}
                          {thread.match_confidence !== null ? ` · ${thread.match_confidence.toFixed(2)}` : ""}
                          {" · "}
                          {thread.message_count} mensaje(s)
                        </span>
                      )}
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

                    <ReplyDraftPanel
                      messageId={message.id}
                      draft={message.reply_assistant_draft ?? null}
                      onRefresh={loadInboxData}
                    />

                    <div className="mt-3 flex items-center justify-between gap-3">
                      <div className="text-xs text-muted-foreground font-data">
                        {message.classification_model
                          ? `${message.classification_role} · ${message.classification_model}`
                          : "Sin clasificación aún"}
                      </div>
                      {(message.classification_status === "pending" || message.classification_status === "failed") && (
                        <Button
                          variant="outline"
                          size="sm"
                          className="rounded-xl gap-1.5"
                          onClick={() => void handleClassifyMessage(message.id)}
                          disabled={classifyingMessageId === message.id}
                        >
                          <Sparkles className="h-3.5 w-3.5" />
                          {classifyingMessageId === message.id ? "Clasificando..." : "Clasificar"}
                        </Button>
                      )}
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        <div className="space-y-6">
          <section className="rounded-2xl border border-border bg-card p-5 shadow-sm">
            <h2 className="font-heading text-base font-semibold text-foreground">Estado del inbox</h2>
            {status ? (
              <div className="mt-4 space-y-3 text-sm text-muted-foreground">
                <div className="flex items-center justify-between gap-3">
                  <span>Provider</span>
                  <span className="font-medium text-foreground">{status.provider}</span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span>Mailbox</span>
                  <code className="rounded-md bg-muted px-2 py-1 text-xs">{status.mailbox}</code>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span>Auto classify</span>
                  <span className="font-medium text-foreground">{status.auto_classify_inbound ? "Activo" : "Manual"}</span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span>Última sync</span>
                  <span className="font-medium text-foreground">
                    {status.last_sync ? status.last_sync.status : "Sin corridas"}
                  </span>
                </div>
                {status.last_sync && (
                  <div className="rounded-xl bg-muted px-3 py-3 text-xs text-muted-foreground">
                    <p>
                      {status.last_sync.new_count} nuevos · {status.last_sync.deduplicated_count} deduplicados
                    </p>
                    <p className="mt-1">
                      {status.last_sync.matched_count} matcheados · {status.last_sync.unmatched_count} unmatched
                    </p>
                    {status.last_sync.completed_at && (
                      <p className="mt-1 font-data">
                        <RelativeTime date={status.last_sync.completed_at} />
                      </p>
                    )}
                    {status.last_sync.error && (
                      <p className="mt-2 text-rose-600">{status.last_sync.error}</p>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <p className="mt-4 text-sm text-muted-foreground">No se pudo leer el estado del inbox.</p>
            )}
          </section>

          <section className="rounded-2xl border border-border bg-card p-5 shadow-sm">
            <h2 className="font-heading text-base font-semibold text-foreground">Threads activos</h2>
            <div className="mt-4 space-y-3">
              {threads.slice(0, 8).map((thread) => {
                const lead = thread.lead_id ? leadById.get(thread.lead_id) : null;
                return (
                  <div key={thread.id} className="rounded-xl border border-border px-3 py-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium text-foreground">
                          {lead ? lead.business_name : "Thread sin lead"}
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {INBOUND_MATCH_VIA_LABELS[thread.matched_via] || thread.matched_via}
                          {thread.match_confidence !== null ? ` · ${thread.match_confidence.toFixed(2)}` : ""}
                        </p>
                      </div>
                      <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                        {thread.message_count} msg
                      </span>
                    </div>
                    <p className="mt-2 text-xs text-muted-foreground font-data">
                      {thread.last_message_at ? (
                        <RelativeTime date={thread.last_message_at} />
                      ) : (
                        "Sin timestamp"
                      )}
                    </p>
                  </div>
                );
              })}
              {threads.length === 0 && (
                <EmptyState
                  icon={MessagesSquare}
                  title="Sin threads todavía"
                  description="A medida que entren replies y hagan match con deliveries, van a aparecer acá."
                  className="py-6"
                />
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

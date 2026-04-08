"use client";

import Link from "next/link";
import { Inbox, Info, Sparkles } from "lucide-react";
import { Skeleton } from "@/components/shared/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { RelativeTime } from "@/components/shared/relative-time";
import {
  InboundClassificationStatusBadge,
  InboundReplyLabelBadge,
} from "@/components/shared/status-badge";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";
import { ReplyDraftPanel } from "@/components/leads/reply-draft-panel";
import { INBOUND_MATCH_VIA_LABELS } from "@/lib/constants";
import { formatDateTime } from "@/lib/formatters";
import type {
  EmailThreadSummary,
  InboundMessage,
  Lead,
  OutreachDraft,
} from "@/types";

interface MessageListProps {
  messages: InboundMessage[];
  loading: boolean;
  filter: "all" | "pending" | "classified" | "failed";
  onFilterChange: (filter: "all" | "pending" | "classified" | "failed") => void;
  leadById: Map<string, Lead>;
  draftById: Map<string, OutreachDraft>;
  threadById: Map<string, EmailThreadSummary>;
  classifyingMessageId: string | null;
  onClassifyMessage: (messageId: string) => void;
  onRefresh: () => void;
}

export function MessageList({
  messages,
  loading,
  filter,
  onFilterChange,
  leadById,
  draftById,
  threadById,
  classifyingMessageId,
  onClassifyMessage,
  onRefresh,
}: MessageListProps) {
  return (
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
              onClick={() => onFilterChange(value)}
              className={`rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors ${
                filter === value
                  ? "bg-muted text-foreground dark:bg-muted dark:text-foreground"
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
            <div key={index} className="rounded-2xl border border-border p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-2 flex-1">
                  <div className="flex gap-2">
                    <Skeleton className="h-5 w-20 rounded-full" />
                    <Skeleton className="h-5 w-24 rounded-full" />
                  </div>
                  <Skeleton className="h-4 w-48" />
                  <Skeleton className="h-3 w-32" />
                </div>
                <Skeleton className="h-4 w-20" />
              </div>
              <div className="mt-3 border-t border-border/50 pt-3 space-y-2">
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-3 w-4/5" />
              </div>
            </div>
          ))}
        </div>
      ) : messages.length === 0 ? (
        <EmptyState
          icon={Inbox}
          title="Sin replies para este filtro"
          description="Todavía no hay respuestas inbound que cumplan este criterio."
          className="py-10"
        />
      ) : (
        <div className="space-y-5">
          {messages.map((message) => {
            const lead = message.lead_id ? leadById.get(message.lead_id) : null;
            const outboundDraft = message.draft_id ? draftById.get(message.draft_id) : null;
            const thread = message.thread_id ? threadById.get(message.thread_id) : null;

            return (
              <article key={message.id} className="rounded-2xl border border-border p-5 space-y-0">
                {/* HEADER: Badges + Sender + Timestamp */}
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="space-y-3">
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
                      <p className="text-base font-semibold text-foreground">
                        {message.from_name || message.from_email || "Reply sin remitente"}
                      </p>
                      <p className="mt-0.5 text-sm text-muted-foreground font-data">
                        {message.subject || "(sin asunto)"}
                      </p>
                    </div>
                  </div>
                  <div className="text-right text-xs text-muted-foreground font-data shrink-0 pt-1">
                    <div>{formatDateTime(message.received_at || message.created_at)}</div>
                    <div className="mt-0.5">
                      <RelativeTime date={message.received_at || message.created_at} />
                    </div>
                  </div>
                </div>

                {/* CONTEXT: Lead link + thread match */}
                {(lead || outboundDraft || thread) && (
                  <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground/70">
                    {lead && (
                      <Link href={`/leads/${lead.id}`} className="rounded-md bg-muted dark:bg-muted px-2 py-0.5 text-foreground dark:text-foreground hover:underline font-medium">
                        {lead.business_name}
                      </Link>
                    )}
                    {outboundDraft && <span className="text-muted-foreground">Draft: {outboundDraft.subject}</span>}
                    {thread && (
                      <span className="text-muted-foreground">
                        {INBOUND_MATCH_VIA_LABELS[thread.matched_via] || thread.matched_via}
                        {thread.match_confidence !== null ? ` · ${thread.match_confidence.toFixed(2)}` : ""}
                        {" · "}
                        {thread.message_count} msg
                      </span>
                    )}
                  </div>
                )}

                {/* CONTENT: Summary + Next step + Body snippet */}
                <div className="mt-4 space-y-3 border-t border-border/40 pt-4">
                  {message.summary && (
                    <p className="text-sm leading-relaxed text-foreground">{message.summary}</p>
                  )}
                  {message.next_action_suggestion && (
                    <div className="flex items-start gap-2 rounded-xl bg-emerald-50/50 dark:bg-emerald-950/10 px-3 py-2.5">
                      <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-400 shrink-0 mt-0.5">Siguiente paso:</span>
                      <span className="text-sm text-foreground/80">{message.next_action_suggestion}</span>
                    </div>
                  )}
                  {message.classification_error && (
                    <p className="text-sm text-rose-600">{message.classification_error}</p>
                  )}
                  {message.body_snippet && (
                    <p className="line-clamp-2 border-l-2 border-muted-foreground/20 pl-3 text-sm text-muted-foreground italic">
                      {message.body_snippet}
                    </p>
                  )}
                </div>

                {/* DRAFT PANEL */}
                <div className="mt-4">
                  <ReplyDraftPanel
                    messageId={message.id}
                    draft={message.reply_assistant_draft ?? null}
                    defaultCollapsed
                    onRefresh={onRefresh}
                  />
                </div>

                {/* FOOTER: Classification info + Classify button */}
                <div className="mt-4 flex items-center justify-between gap-3 border-t border-border/40 pt-3">
                  <div className="text-xs text-muted-foreground/60 font-data">
                    {message.classification_model ? (
                      <Tooltip>
                        <TooltipTrigger className="inline-flex items-center gap-1 cursor-default">
                          <Info className="h-3 w-3" />
                          <span>Clasificado</span>
                        </TooltipTrigger>
                        <TooltipContent>
                          {message.classification_role} · {message.classification_model}
                        </TooltipContent>
                      </Tooltip>
                    ) : (
                      "Sin clasificación aún"
                    )}
                  </div>
                  {(message.classification_status === "pending" || message.classification_status === "failed") && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="rounded-xl gap-1.5"
                      onClick={() => onClassifyMessage(message.id)}
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
  );
}

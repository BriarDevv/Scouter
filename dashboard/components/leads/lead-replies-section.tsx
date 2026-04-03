"use client";

import { CollapsibleSection } from "@/components/shared/collapsible-section";
import { EmptyState } from "@/components/shared/empty-state";
import {
  InboundClassificationStatusBadge,
  InboundReplyLabelBadge,
} from "@/components/shared/status-badge";
import { INBOUND_MATCH_VIA_LABELS } from "@/lib/constants";
import { RelativeTime } from "@/components/shared/relative-time";
import { ReplyDraftPanel } from "@/components/shared/reply-draft-panel";
import { formatDateTime } from "@/lib/formatters";
import { MessageSquare } from "lucide-react";
import type { InboundMessage, EmailThreadSummary } from "@/types";

interface LeadRepliesSectionProps {
  inboundMessages: InboundMessage[];
  inboundThreads: EmailThreadSummary[];
  onRefresh: () => void;
}

export function LeadRepliesSection({ inboundMessages, inboundThreads, onRefresh }: LeadRepliesSectionProps) {
  const threadById = new Map<string, EmailThreadSummary>(inboundThreads.map((thread) => [thread.id, thread]));
  const latestInboundMessage = inboundMessages[0] ?? null;

  return (
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
            onRefresh={onRefresh}
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
  );
}

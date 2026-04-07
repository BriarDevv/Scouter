"use client";

import { FileText } from "lucide-react";
import { EmptyState } from "@/components/shared/empty-state";
import { RelativeTime } from "@/components/shared/relative-time";
import { DraftStatusBadge, InboundClassificationStatusBadge, InboundReplyLabelBadge } from "@/components/shared/status-badge";
import { INBOUND_MATCH_VIA_LABELS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import type { EmailThreadSummary, InboundMessage, OutreachDelivery, OutreachDraft } from "@/types";

interface DraftDetailProps {
  selectedDraft: OutreachDraft | null;
  selectedDeliveries: OutreachDelivery[];
  selectedReplies: InboundMessage[];
  selectedThreads: EmailThreadSummary[];
  mailError: string | null;
}

export function DraftDetail({
  selectedDraft,
  selectedDeliveries,
  selectedReplies,
  selectedThreads,
  mailError,
}: DraftDetailProps) {
  return (
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
  );
}

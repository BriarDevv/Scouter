"use client";

import { MessagesSquare } from "lucide-react";
import { CollapsibleSection } from "@/components/shared/collapsible-section";
import { EmptyState } from "@/components/shared/empty-state";
import { RelativeTime } from "@/components/shared/relative-time";
import { INBOUND_MATCH_VIA_LABELS } from "@/lib/constants";
import type { EmailThreadSummary, InboundMailStatus, Lead } from "@/types";

interface ThreadDetailProps {
  threads: EmailThreadSummary[];
  status: InboundMailStatus | null;
  leadById: Map<string, Lead>;
}

export function ThreadDetail({ threads, status, leadById }: ThreadDetailProps) {
  return (
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

      <CollapsibleSection
        title="Threads activos"
        icon={MessagesSquare}
        badge={
          threads.length > 0 ? (
            <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
              {threads.length}
            </span>
          ) : undefined
        }
        defaultOpen={threads.length <= 5}
      >
        <div className="space-y-3">
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
      </CollapsibleSection>
    </div>
  );
}

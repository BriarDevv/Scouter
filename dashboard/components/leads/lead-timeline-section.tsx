"use client";

import { CollapsibleSection } from "@/components/shared/collapsible-section";
import { formatDateTime } from "@/lib/formatters";
import { Clock, StickyNote } from "lucide-react";
import type { OutreachLog } from "@/types";

interface LeadTimelineSectionProps {
  logs: OutreachLog[];
  notes: string | null | undefined;
}

export function LeadTimelineSection({ logs, notes }: LeadTimelineSectionProps) {
  return (
    <>
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

      {notes && (
        <CollapsibleSection
          title="Notas"
          icon={StickyNote}
          defaultOpen
        >
          <p className="text-sm text-muted-foreground">{notes}</p>
        </CollapsibleSection>
      )}
    </>
  );
}

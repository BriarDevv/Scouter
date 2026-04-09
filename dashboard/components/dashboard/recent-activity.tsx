"use client";

import Link from "next/link";
import type { Lead, OutreachLog } from "@/types";
import { RelativeTime } from "@/components/shared/relative-time";
import {
  FileText, Send, Eye, MessageSquare, CalendarCheck, Trophy, XCircle, CheckCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";

const ACTION_META: Record<string, { icon: typeof FileText; label: string }> = {
  generated: { icon: FileText,      label: "Draft generado" },
  sent:      { icon: Send,          label: "Enviado" },
  opened:    { icon: Eye,           label: "Abierto" },
  replied:   { icon: MessageSquare, label: "Respondio" },
  meeting:   { icon: CalendarCheck, label: "Reunion" },
  won:       { icon: Trophy,        label: "Ganado" },
  lost:      { icon: XCircle,       label: "Perdido" },
  approved:  { icon: CheckCircle,   label: "Aprobado" },
  rejected:  { icon: XCircle,       label: "Rechazado" },
  reviewed:  { icon: Eye,           label: "Revisado" },
};

export function RecentActivity({ logs, leads }: { logs: OutreachLog[]; leads?: Lead[] }) {
  const items = logs.slice(0, 8);

  return (
    <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
      <h3 className="text-sm font-semibold text-foreground font-heading">Actividad Reciente</h3>
      <p className="mt-0.5 text-xs text-muted-foreground">Ultimas acciones del pipeline</p>

      {items.length === 0 ? (
        <p className="mt-6 text-center text-xs text-muted-foreground py-4">Sin actividad reciente</p>
      ) : (
        <div className="mt-4 space-y-px">
          {items.map((log) => {
            const meta = ACTION_META[log.action] || ACTION_META.generated;
            const Icon = meta.icon;
            const lead = leads?.find((item) => item.id === log.lead_id);
            const name = log.business_name || lead?.business_name;

            return (
              <div
                key={log.id}
                className="relative flex items-center gap-3 rounded-lg px-3 py-2.5 transition-colors hover:bg-muted/50"
              >
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-muted/60">
                  <Icon className="h-3.5 w-3.5 text-muted-foreground" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    {name ? (
                      <Link href={`/leads/${log.lead_id}`} className="text-xs font-medium text-foreground hover:underline truncate">
                        {name}
                      </Link>
                    ) : (
                      <Link href={`/leads/${log.lead_id}`} className="text-xs text-muted-foreground hover:underline">
                        Ver lead
                      </Link>
                    )}
                    <span className="text-[10px] text-muted-foreground/60">{meta.label}</span>
                  </div>
                </div>
                <RelativeTime
                  date={log.created_at}
                  className="shrink-0 text-[10px] text-muted-foreground font-data"
                />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

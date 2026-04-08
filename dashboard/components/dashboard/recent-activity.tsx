"use client";

import type { Lead, OutreachLog } from "@/types";
import { RelativeTime } from "@/components/shared/relative-time";
import {
  FileText, Send, Eye, MessageSquare, CalendarCheck, Trophy, XCircle, CheckCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";

const ACTION_ICONS: Record<string, { icon: typeof FileText; color: string; bg: string }> = {
  generated: { icon: FileText,       color: "text-muted-foreground",   bg: "bg-muted" },
  sent:      { icon: Send,           color: "text-blue-600",    bg: "bg-blue-50" },
  opened:    { icon: Eye,            color: "text-amber-600",   bg: "bg-amber-50" },
  replied:   { icon: MessageSquare,  color: "text-emerald-600", bg: "bg-emerald-50" },
  meeting:   { icon: CalendarCheck,  color: "text-teal-600",    bg: "bg-teal-50" },
  won:       { icon: Trophy,         color: "text-green-600",   bg: "bg-green-50" },
  lost:      { icon: XCircle,        color: "text-red-500",     bg: "bg-red-50" },
  approved:  { icon: CheckCircle,    color: "text-foreground",  bg: "bg-muted" },
  rejected:  { icon: XCircle,        color: "text-red-500",     bg: "bg-red-50" },
  reviewed:  { icon: Eye,            color: "text-indigo-600",  bg: "bg-indigo-50" },
};

export function RecentActivity({ logs, leads }: { logs: OutreachLog[]; leads?: Lead[] }) {
  return (
    <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
      <h3 className="text-sm font-semibold text-foreground font-heading">Actividad Reciente</h3>
      <p className="mt-0.5 text-xs text-muted-foreground">Últimas acciones del pipeline</p>

      <div className="mt-4 space-y-1">
        {logs.slice(0, 8).map((log) => {
          const actionConfig = ACTION_ICONS[log.action] || ACTION_ICONS.generated;
          const Icon = actionConfig.icon;
          const lead = leads?.find((item) => item.id === log.lead_id);

          return (
            <div key={log.id} className="flex items-center gap-3 rounded-xl px-2 py-2.5 transition-colors hover:bg-muted">
              <div className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-lg", actionConfig.bg)}>
                <Icon className={cn("h-4 w-4", actionConfig.color)} />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm text-foreground/80">
                  <span className="font-medium">{lead?.business_name || "Lead"}</span>
                  {log.detail && <span className="text-muted-foreground"> — {log.detail}</span>}
                </p>
              </div>
              <RelativeTime
                date={log.created_at}
                className="shrink-0 text-xs text-muted-foreground font-data"
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}

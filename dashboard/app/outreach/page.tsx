"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { DraftStatusBadge, StatusBadge } from "@/components/shared/status-badge";
import { formatRelativeTime, formatDate, truncate } from "@/lib/formatters";
import { MOCK_DRAFTS, MOCK_LOGS, MOCK_LEADS } from "@/data/mock";
import { getDrafts, getLeads, getOutreachLogs, reviewDraft } from "@/lib/api/client";
import type { DraftStatus, OutreachDraft, OutreachLog } from "@/types";
import { DRAFT_STATUS_CONFIG } from "@/lib/constants";
import {
  Mail, CheckCircle, XCircle, Send, Eye, MessageSquare,
  CalendarCheck, Trophy, FileText, Clock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import Link from "next/link";

const ACTION_CONFIG: Record<string, { icon: typeof FileText; label: string; color: string }> = {
  generated: { icon: FileText, label: "Draft generado", color: "text-slate-500" },
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
  const [isReviewingDraftId, setIsReviewingDraftId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadOutreachData() {
      const [nextDrafts, nextLogs, nextLeads] = await Promise.all([
        getDrafts(),
        getOutreachLogs({ limit: 50 }),
        getLeads({ page: 1, page_size: 200 }),
      ]);

      if (!active) {
        return;
      }

      setDrafts(nextDrafts);
      setLogs(nextLogs);
      setLeads(nextLeads.items);
      setSelectedDraft((current) =>
        current ? nextDrafts.find((draft) => draft.id === current.id) ?? null : nextDrafts[0] ?? null
      );
    }

    void loadOutreachData();

    return () => {
      active = false;
    };
  }, []);

  const filteredDrafts = filter === "all"
    ? drafts
    : drafts.filter((d) => d.status === filter);

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
                    : "bg-white text-slate-500 hover:bg-slate-50 border border-slate-200"
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
                    "cursor-pointer rounded-2xl border bg-white p-5 shadow-sm transition-all hover:shadow-md",
                    selectedDraft?.id === draft.id ? "border-violet-200 ring-1 ring-violet-100" : "border-slate-100"
                  )}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-1.5">
                        <DraftStatusBadge status={draft.status} />
                        {lead && (
                          <Link href={`/leads/${lead.id}`} className="text-xs text-slate-500 hover:text-violet-600 transition-colors">
                            {lead.business_name}
                          </Link>
                        )}
                      </div>
                      <h4 className="text-sm font-medium text-slate-900 font-heading">{draft.subject}</h4>
                      <p className="mt-1 text-sm text-slate-500 line-clamp-2">{draft.body}</p>
                    </div>
                    <span className="shrink-0 text-xs text-slate-400 font-data">{formatRelativeTime(draft.generated_at)}</span>
                  </div>

                  {draft.status === "pending_review" && (
                    <div className="mt-3 flex gap-2 border-t border-slate-50 pt-3">
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
              <div className="rounded-2xl border border-slate-100 bg-white p-12 text-center">
                <Mail className="mx-auto h-8 w-8 text-slate-300" />
                <p className="mt-3 text-sm text-slate-500">No hay drafts con este filtro</p>
              </div>
            )}
          </div>
        </div>

        {/* Right: Activity Feed */}
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-slate-900 font-heading">Actividad Reciente</h3>

          <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm">
            <div className="space-y-1">
              {logs.map((log) => {
                const config = ACTION_CONFIG[log.action] || ACTION_CONFIG.generated;
                const Icon = config.icon;
                const lead = leads.find((item) => item.id === log.lead_id);

                return (
                  <div key={log.id} className="flex items-start gap-3 rounded-xl px-2 py-2.5 hover:bg-slate-50 transition-colors">
                    <Icon className={cn("h-4 w-4 mt-0.5 shrink-0", config.color)} />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-slate-700">
                        <span className="font-medium">{config.label}</span>
                        {lead && <span className="text-slate-500"> — {lead.business_name}</span>}
                      </p>
                      {log.detail && <p className="text-xs text-slate-500 mt-0.5">{log.detail}</p>}
                      <p className="text-xs text-slate-400 mt-0.5 flex items-center gap-1 font-data">
                        <Clock className="h-3 w-3" />
                        {formatRelativeTime(log.created_at)}
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

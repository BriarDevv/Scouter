"use client";

import Link from "next/link";
import { Mail, CheckCircle, XCircle, Loader2, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/shared/empty-state";
import { RelativeTime } from "@/components/shared/relative-time";
import { DraftStatusBadge } from "@/components/shared/status-badge";
import { cn } from "@/lib/utils";
import type { DraftStatus, Lead, OutreachDraft } from "@/types";
import { DRAFT_STATUS_CONFIG } from "@/lib/constants";

const FILTER_OPTIONS: (DraftStatus | "all")[] = ["all", "pending_review", "approved", "sent", "rejected"];

interface DraftListProps {
  drafts: OutreachDraft[];
  filteredDrafts: OutreachDraft[];
  leads: Lead[];
  filter: DraftStatus | "all";
  onFilterChange: (filter: DraftStatus | "all") => void;
  selectedDraft: OutreachDraft | null;
  onSelectDraft: (draft: OutreachDraft) => void;
  isReviewingDraftId: string | null;
  isSendingDraftId: string | null;
  onReview: (draftId: string, approved: boolean) => void;
  onSend: (draftId: string) => void;
}

export function DraftList({
  drafts,
  filteredDrafts,
  leads,
  filter,
  onFilterChange,
  selectedDraft,
  onSelectDraft,
  isReviewingDraftId,
  isSendingDraftId,
  onReview,
  onSend,
}: DraftListProps) {
  const countByStatus = (status: DraftStatus) => drafts.filter((d) => d.status === status).length;

  return (
    <div className="lg:col-span-2 space-y-4">
      {/* Tab-style filters with counts */}
      <div className="flex items-center gap-0 border-b border-border">
        {FILTER_OPTIONS.map((s) => {
          const isActive = filter === s;
          const count = s === "all" ? drafts.length : countByStatus(s);
          return (
            <button
              key={s}
              onClick={() => onFilterChange(s)}
              className={cn(
                "relative px-3 py-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "text-foreground dark:text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {s === "all" ? "Todos" : DRAFT_STATUS_CONFIG[s].label}
              <span className={cn(
                "ml-1.5 rounded-full px-1.5 py-0.5 text-xs",
                isActive ? "bg-muted dark:bg-muted text-foreground dark:text-foreground" : "bg-muted text-muted-foreground"
              )}>
                {count}
              </span>
              {isActive && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-foreground dark:bg-foreground rounded-full" />
              )}
            </button>
          );
        })}
      </div>

      {/* Drafts */}
      <div className="space-y-3">
        {filteredDrafts.map((draft) => {
          const lead = draft.lead ?? leads.find((item) => item.id === draft.lead_id);
          const isSelected = selectedDraft?.id === draft.id;
          return (
            <div
              key={draft.id}
              onClick={() => onSelectDraft(draft)}
              className={cn(
                "cursor-pointer rounded-2xl border bg-card p-5 shadow-sm transition-all hover:shadow-md",
                isSelected
                  ? "border-l-4 border-l-foreground border-border dark:border-border"
                  : "border-border"
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-1.5">
                    <DraftStatusBadge status={draft.status} />
                    {draft.channel === "whatsapp" ? (
                      <span className="inline-flex items-center rounded-md bg-emerald-50 dark:bg-emerald-950/40 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700 dark:text-emerald-300">
                        WA
                      </span>
                    ) : (
                      <span className="inline-flex items-center rounded-md bg-blue-50 dark:bg-blue-950/40 px-1.5 py-0.5 text-[10px] font-medium text-blue-700 dark:text-blue-300">
                        Email
                      </span>
                    )}
                    {lead && (
                      <Link href={`/leads/${lead.id}`} className="text-xs text-muted-foreground hover:text-foreground transition-colors">
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
                    onClick={(e) => { e.stopPropagation(); onReview(draft.id, true); }}
                    disabled={isReviewingDraftId === draft.id}
                  >
                    {isReviewingDraftId === draft.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle className="h-3.5 w-3.5" />}
                    Aprobar
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="rounded-xl gap-1.5 h-8 text-red-600 border-red-200 hover:bg-red-50 dark:hover:bg-red-950/20"
                    onClick={(e) => { e.stopPropagation(); onReview(draft.id, false); }}
                    disabled={isReviewingDraftId === draft.id}
                  >
                    <XCircle className="h-3.5 w-3.5" /> Rechazar
                  </Button>
                </div>
              )}

              {draft.status === "approved" && (
                <div className="mt-3 flex gap-2 border-t border-border/50 pt-3">
                  <Button
                    size="sm"
                    className="rounded-xl bg-blue-600 text-white hover:bg-blue-700 gap-1.5 h-8"
                    onClick={(e) => { e.stopPropagation(); onSend(draft.id); }}
                    disabled={isSendingDraftId === draft.id}
                  >
                    {isSendingDraftId === draft.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                    Enviar Mail
                  </Button>
                </div>
              )}
            </div>
          );
        })}

        {filteredDrafts.length === 0 && (
          <EmptyState
            icon={Mail}
            title="Sin drafts"
            description="No hay drafts con este filtro."
          />
        )}
      </div>
    </div>
  );
}

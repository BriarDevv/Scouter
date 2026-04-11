"use client";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/shared/empty-state";
import { RelativeTime } from "@/components/shared/relative-time";
import { FileText, CheckCircle, XCircle, Loader2, Mail, MessageCircle, Send } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Lead, OutreachDraft } from "@/types";

interface LeadOutreachSectionProps {
  lead: Lead;
  drafts: OutreachDraft[];
  isGeneratingDraft: boolean;
  isReviewingDraftId: string | null;
  isSendingDraftId: string | null;
  onGenerateDraft: () => void;
  onReviewDraft: (draftId: string, approved: boolean) => void;
  onSendDraft: (draftId: string) => void;
}

export function LeadOutreachSection({
  lead,
  drafts,
  isGeneratingDraft,
  isReviewingDraftId,
  isSendingDraftId,
  onGenerateDraft,
  onReviewDraft,
  onSendDraft,
}: LeadOutreachSectionProps) {
  return (
    <div className="space-y-4">
      {/* Generate buttons */}
      <div className="flex items-center gap-2">
        {lead.email && (
          <Button
            variant="outline"
            size="sm"
            className="rounded-xl gap-1.5"
            onClick={onGenerateDraft}
            disabled={isGeneratingDraft}
          >
            {isGeneratingDraft ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Mail className="h-3.5 w-3.5" />}
            Generar draft email
          </Button>
        )}
      </div>

      {/* Drafts list */}
      {drafts.length > 0 ? (
        <div className="space-y-3">
          {drafts.map((draft) => {
            const isWhatsApp = draft.channel === "whatsapp";
            const ChannelIcon = isWhatsApp ? MessageCircle : Mail;

            return (
              <div key={draft.id} className="rounded-2xl border border-border bg-card p-4 shadow-sm">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <ChannelIcon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                    <span className="text-sm font-medium text-foreground truncate">
                      {draft.subject || (isWhatsApp ? "WhatsApp" : "Email")}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-[10px] text-muted-foreground font-data">
                      <RelativeTime date={draft.generated_at} />
                    </span>
                    <span className={cn(
                      "rounded-full px-2 py-0.5 text-[10px] font-medium",
                      draft.status === "pending_review" && "bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-300",
                      draft.status === "approved" && "bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300",
                      draft.status === "sent" && "bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300",
                      draft.status === "rejected" && "bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300",
                    )}>
                      {draft.status === "pending_review" ? "Pendiente" : draft.status === "approved" ? "Aprobado" : draft.status === "sent" ? "Enviado" : "Rechazado"}
                    </span>
                  </div>
                </div>
                <p className="text-sm text-muted-foreground whitespace-pre-line leading-relaxed">{draft.body}</p>
                <div className="mt-3 flex gap-2">
                  {draft.status === "pending_review" && (
                    <>
                      <Button
                        variant="success"
                        size="sm"
                        className="rounded-xl gap-1.5"
                        onClick={() => onReviewDraft(draft.id, true)}
                        disabled={isReviewingDraftId === draft.id}
                      >
                        {isReviewingDraftId === draft.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle className="h-3.5 w-3.5" />}
                        Aprobar
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="rounded-xl gap-1.5 text-red-600 border-red-200 hover:bg-red-50 dark:hover:bg-red-950/20"
                        onClick={() => onReviewDraft(draft.id, false)}
                        disabled={isReviewingDraftId === draft.id}
                      >
                        <XCircle className="h-3.5 w-3.5" /> Rechazar
                      </Button>
                    </>
                  )}
                  {draft.status === "approved" && (
                    <Button
                      size="sm"
                      className="rounded-xl gap-1.5"
                      onClick={() => onSendDraft(draft.id)}
                      disabled={isSendingDraftId === draft.id}
                    >
                      {isSendingDraftId === draft.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                      Enviar
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <EmptyState
          icon={FileText}
          title="Sin borradores"
          description="Generá un borrador de outreach para este lead."
          className="py-6"
        >
          {lead.email && (
            <Button
              variant="outline"
              size="sm"
              className="rounded-xl gap-1.5"
              onClick={onGenerateDraft}
              disabled={isGeneratingDraft}
            >
              {isGeneratingDraft ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Mail className="h-3.5 w-3.5" />}
              Generar Draft
            </Button>
          )}
        </EmptyState>
      )}
    </div>
  );
}

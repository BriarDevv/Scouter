"use client";

import { Button } from "@/components/ui/button";
import { CollapsibleSection } from "@/components/shared/collapsible-section";
import { EmptyState } from "@/components/shared/empty-state";
import { RelativeTime } from "@/components/shared/relative-time";
import { FileText, CheckCircle, XCircle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { OutreachDraft } from "@/types";

interface LeadOutreachSectionProps {
  drafts: OutreachDraft[];
  isGeneratingDraft: boolean;
  isReviewingDraftId: string | null;
  onGenerateDraft: () => void;
  onReviewDraft: (draftId: string, approved: boolean) => void;
}

export function LeadOutreachSection({
  drafts,
  isGeneratingDraft,
  isReviewingDraftId,
  onGenerateDraft,
  onReviewDraft,
}: LeadOutreachSectionProps) {
  return (
    <CollapsibleSection
      title="Borradores de Outreach"
      icon={FileText}
      defaultOpen
      badge={
        drafts.length > 0 ? (
          <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">{drafts.length}</span>
        ) : undefined
      }
    >
      {drafts.length > 0 ? (
        <div className="space-y-3">
          {drafts.map((draft) => (
            <div key={draft.id} className="rounded-xl border border-border p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-foreground">{draft.subject}</span>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground font-data">
                    <RelativeTime date={draft.generated_at} />
                  </span>
                  <span className={cn(
                    "rounded-full px-2 py-0.5 text-xs font-medium",
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
              {draft.status === "pending_review" && (
                <div className="mt-3 flex gap-2">
                  <Button
                    size="sm"
                    className="rounded-xl bg-emerald-600 text-white hover:bg-emerald-700 gap-1.5"
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
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={FileText}
          title="Sin borradores"
          description="Generá un borrador de outreach para este lead."
          className="py-6"
        >
          <Button
            variant="outline"
            size="sm"
            className="rounded-xl gap-1.5"
            onClick={onGenerateDraft}
            disabled={isGeneratingDraft}
          >
            {isGeneratingDraft ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileText className="h-3.5 w-3.5" />}
            Generar Draft
          </Button>
        </EmptyState>
      )}
    </CollapsibleSection>
  );
}

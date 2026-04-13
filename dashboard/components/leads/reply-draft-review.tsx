import type { ReplyAssistantDraft } from "@/types";

// ─── Full review section ──────────────────────────────

interface ReplyDraftReviewProps {
  draft: ReplyAssistantDraft;
  compact: boolean;
}

export function ReplyDraftReview({ draft, compact }: ReplyDraftReviewProps) {
  if (!draft.review) return null;

  // ─── Compact review summary ─────────────────────────
  if (compact) {
    return (
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
        <span className="font-medium text-foreground/80">Review:</span>
        {draft.review.recommended_action && (
          <span className="text-muted-foreground">{draft.review.recommended_action}</span>
        )}
        {draft.review.should_use_as_is && (
          <span className="rounded-full bg-emerald-50 dark:bg-emerald-950/30 px-2 py-0.5 font-medium text-emerald-700">
            Usable
          </span>
        )}
        {draft.review.should_edit && (
          <span className="rounded-full bg-amber-50 dark:bg-amber-950/30 px-2 py-0.5 font-medium text-amber-700">
            Editar
          </span>
        )}
        {draft.review.should_escalate && (
          <span className="rounded-full bg-fuchsia-50 dark:bg-fuchsia-950/30 px-2 py-0.5 font-medium text-fuchsia-700">
            Escalar
          </span>
        )}
      </div>
    );
  }

  // ─── Full review section ────────────────────────────
  return (
    <div className="mt-5 rounded-xl border border-fuchsia-100 dark:border-fuchsia-900/30 bg-fuchsia-50/40 dark:bg-fuchsia-950/10 p-4 space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-foreground font-heading">Review del draft</p>
          <p className="mt-1 text-[11px] text-muted-foreground/60 font-data">
            {draft.review.reviewer_role || "reviewer"} ·{" "}
            {draft.review.reviewer_model || "modelo no informado"}
          </p>
        </div>
        <span className="rounded-full bg-card px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
          {draft.review.status}
        </span>
      </div>
      {draft.review.summary && (
        <p className="text-sm leading-relaxed text-foreground/80">{draft.review.summary}</p>
      )}
      {draft.review.feedback && (
        <div className="rounded-lg bg-card/60 px-3 py-2.5">
          <p className="text-xs font-semibold text-foreground/70 mb-1">Feedback</p>
          <p className="text-sm text-foreground/80">{draft.review.feedback}</p>
        </div>
      )}
      {draft.review.recommended_action && (
        <div className="rounded-lg bg-card/60 px-3 py-2.5">
          <p className="text-xs font-semibold text-foreground/70 mb-1">Acción recomendada</p>
          <p className="text-sm text-foreground/80">{draft.review.recommended_action}</p>
        </div>
      )}
      {draft.review.suggested_edits && draft.review.suggested_edits.length > 0 && (
        <div className="rounded-lg bg-card/60 px-3 py-2.5">
          <p className="text-xs font-semibold text-foreground/70 mb-2">Sugerencias de edición</p>
          <ul className="list-disc space-y-1 pl-4 text-sm text-foreground/80">
            {draft.review.suggested_edits.map((edit, index) => (
              <li key={`${draft.review?.id}-edit-${index}`}>{edit}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="flex flex-wrap gap-2 text-xs pt-1">
        {draft.review.should_use_as_is && (
          <span className="rounded-full bg-emerald-50 dark:bg-emerald-950/30 px-2.5 py-0.5 font-medium text-emerald-700 dark:text-emerald-300">
            Usable tal cual
          </span>
        )}
        {draft.review.should_edit && (
          <span className="rounded-full bg-amber-50 dark:bg-amber-950/30 px-2.5 py-0.5 font-medium text-amber-700 dark:text-amber-300">
            Conviene editar
          </span>
        )}
        {draft.review.should_escalate && (
          <span className="rounded-full bg-fuchsia-50 dark:bg-fuchsia-950/30 px-2.5 py-0.5 font-medium text-fuchsia-700 dark:text-fuchsia-300">
            Mejor escalar
          </span>
        )}
      </div>
      {draft.review.error && (
        <p className="text-sm text-rose-600">{draft.review.error}</p>
      )}
    </div>
  );
}

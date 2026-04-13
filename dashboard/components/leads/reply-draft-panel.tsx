"use client";

import { useEffect, useState } from "react";
import {
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Edit3,
  LifeBuoy,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { RelativeTime } from "@/components/shared/relative-time";
import {
  generateReplyAssistantDraft,
  requestReplyAssistantDraftReview,
} from "@/lib/api/client";
import { cn } from "@/lib/utils";
import type { ReplyAssistantDraft } from "@/types";

import { SendStatusBadge } from "./reply-draft-send-status";
import { ReplyDraftEditor } from "./reply-draft-editor";
import { ReplyDraftSendStatus } from "./reply-draft-send-status";
import { ReplyDraftReview } from "./reply-draft-review";

// ─── Props ─────────────────────────────────────────────

interface ReplyDraftPanelProps {
  messageId: string;
  draft: ReplyAssistantDraft | null;
  compact?: boolean;
  defaultCollapsed?: boolean;
  onRefresh: () => void | Promise<void>;
}

// ─── Collapsed summary line ──────────────────────────────

function CollapsedSummary({
  draft,
  onExpand,
}: {
  draft: ReplyAssistantDraft | null;
  onExpand: () => void;
}) {
  let statusText: string;
  if (!draft) {
    statusText = "Sin draft";
  } else if (draft.latest_send?.status === "sent") {
    statusText = "Enviado";
  } else {
    statusText = "Draft pendiente · No enviado";
  }

  return (
    <button
      type="button"
      onClick={onExpand}
      className="mt-3 flex w-full items-center justify-between gap-3 rounded-xl border border-border bg-muted/50 dark:bg-muted/50 px-3 py-2 text-left transition-colors hover:bg-muted dark:hover:bg-muted"
    >
      <span className="text-xs font-medium text-foreground/70">{statusText}</span>
      <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
    </button>
  );
}

// ─── Panel ─────────────────────────────────────────────

export function ReplyDraftPanel({
  messageId,
  draft,
  compact = false,
  defaultCollapsed = true,
  onRefresh,
}: ReplyDraftPanelProps) {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [isEditing, setIsEditing] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [reviewing, setReviewing] = useState(false);

  // Reset edit state when draft changes
  useEffect(() => {
    setIsEditing(false);
  }, [draft?.id, draft?.updated_at]);

  async function handleGenerate() {
    setGenerating(true);
    try {
      await generateReplyAssistantDraft(messageId);
      await onRefresh();
    } catch (err) {
      console.error("reply_draft_generate_failed", err);
    } finally {
      setGenerating(false);
    }
  }

  async function handleReview() {
    setReviewing(true);
    try {
      await requestReplyAssistantDraftReview(messageId);
      await onRefresh();
    } catch (err) {
      console.error("reply_draft_review_request_failed", err);
    } finally {
      setReviewing(false);
    }
  }

  // ─── Collapsed mode ─────────────────────────────────
  if (isCollapsed) {
    return <CollapsedSummary draft={draft} onExpand={() => setIsCollapsed(false)} />;
  }

  // ─── No draft yet ────────────────────────────────────
  if (!draft) {
    return (
      <div className={cn(
        "rounded-2xl border border-border bg-muted/50 dark:bg-muted/50",
        compact ? "p-4" : "p-5"
      )}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className={cn("font-semibold text-foreground font-heading", compact ? "text-xs" : "text-sm")}>
            Draft de respuesta sugerido
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="rounded-xl gap-1.5"
              onClick={() => void handleGenerate()}
              disabled={generating}
            >
              <Sparkles className="h-3.5 w-3.5" />
              {generating ? "Generando..." : "Generar draft"}
            </Button>
            <button
              type="button"
              onClick={() => setIsCollapsed(true)}
              className="rounded-lg p-1 text-muted-foreground hover:bg-muted transition-colors"
            >
              <ChevronUp className="h-4 w-4" />
            </button>
          </div>
        </div>
        <p className="mt-3 text-sm text-muted-foreground">
          Todavía no hay draft sugerido para esta reply.
        </p>
      </div>
    );
  }

  // ─── Draft exists ────────────────────────────────────
  return (
    <div className={cn(
      "rounded-2xl border border-border bg-muted/50 dark:bg-muted/50",
      compact ? "p-4" : "p-5"
    )}>
      {/* ── HEADER ── */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          <p className={cn("font-semibold text-foreground font-heading", compact ? "text-xs" : "text-sm")}>
            Draft de respuesta sugerido
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <SendStatusBadge draft={draft} />
            {draft.review_is_stale && (
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 dark:bg-amber-950/30 px-2.5 py-0.5 text-xs font-medium text-amber-700">
                <AlertTriangle className="h-3 w-3" /> Review desactualizado
              </span>
            )}
            {draft.edited_at && (
              <span className="inline-flex items-center gap-1 rounded-full bg-sky-50 dark:bg-sky-950/30 px-2.5 py-0.5 text-xs font-medium text-sky-700 dark:text-sky-300">
                <Edit3 className="h-3 w-3" /> Editado
              </span>
            )}
            {draft.should_escalate_reviewer && (
              <span className="inline-flex items-center rounded-full bg-fuchsia-50 dark:bg-fuchsia-950/30 px-2.5 py-0.5 text-xs font-medium text-fuchsia-700">
                Conviene reviewer
              </span>
            )}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="rounded-xl gap-1.5"
            onClick={() => void handleGenerate()}
            disabled={generating}
          >
            <RotateCcw className="h-3.5 w-3.5" />
            {generating ? "Regenerando..." : "Regenerar"}
          </Button>
          {!compact && (
            <Button
              variant="outline"
              size="sm"
              className="rounded-xl gap-1.5"
              onClick={() => void handleReview()}
              disabled={reviewing}
            >
              <LifeBuoy className="h-3.5 w-3.5" />
              {reviewing
                ? "Pidiendo..."
                : draft.review
                  ? "Re-review"
                  : "Pedir review"}
            </Button>
          )}
          <button
            type="button"
            onClick={() => setIsCollapsed(true)}
            className="rounded-lg p-1 text-muted-foreground hover:bg-muted transition-colors"
          >
            <ChevronUp className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* ── META (smaller, de-emphasized) ── */}
      {!compact && (
        <div className="mt-3 flex flex-wrap gap-3 text-[11px] text-muted-foreground/60 font-data">
          {draft.suggested_tone && <span>Tono: {draft.suggested_tone}</span>}
          <span>{draft.generator_role} · {draft.generator_model}</span>
          <span><RelativeTime date={draft.updated_at} /></span>
          {draft.edited_at && (
            <span>
              Editado <RelativeTime date={draft.edited_at} />
              {draft.edited_by && <> por {draft.edited_by}</>}
            </span>
          )}
        </div>
      )}

      {/* ── SUMMARY ── */}
      {draft.summary && !compact && (
        <p className="mt-4 text-sm leading-relaxed text-foreground/80">{draft.summary}</p>
      )}

      {/* ── SUBJECT / BODY — edit or view ── */}
      <ReplyDraftEditor
        messageId={messageId}
        draft={draft}
        compact={compact}
        isEditing={isEditing}
        onEditingChange={setIsEditing}
        onRefresh={onRefresh}
      />

      {/* ── SEND STATUS / ACTIONS ── */}
      <ReplyDraftSendStatus
        messageId={messageId}
        draft={draft}
        isEditing={isEditing}
        onRefresh={onRefresh}
      />

      {/* ── REVIEW ── */}
      <ReplyDraftReview draft={draft} compact={compact} />
    </div>
  );
}

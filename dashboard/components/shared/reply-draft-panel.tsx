"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  Check,
  ChevronDown,
  ChevronUp,
  Edit3,
  Loader2,
  Lock,
  Save,
  Send,
  Sparkles,
  LifeBuoy,
  RotateCcw,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { RelativeTime } from "@/components/shared/relative-time";
import {
  generateReplyAssistantDraft,
  requestReplyAssistantDraftReview,
  updateReplyAssistantDraft,
  sendReplyAssistantDraft,
  getReplyAssistantSendStatus,
} from "@/lib/api/client";
import { cn } from "@/lib/utils";
import type { ReplyAssistantDraft, ReplyAssistantSendStatusResponse } from "@/types";

// ─── Send status badge ────────────────────────────────

function SendStatusBadge({ draft }: { draft: ReplyAssistantDraft }) {
  const send = draft.latest_send;
  if (!send) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
        No enviado
      </span>
    );
  }
  switch (send.status) {
    case "sending":
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 dark:bg-blue-950/30 px-2.5 py-0.5 text-xs font-medium text-blue-700">
          <Loader2 className="h-3 w-3 animate-spin" /> Enviando
        </span>
      );
    case "sent":
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 dark:bg-emerald-950/30 px-2.5 py-0.5 text-xs font-medium text-emerald-700">
          <Check className="h-3 w-3" /> Enviado
        </span>
      );
    case "failed":
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 dark:bg-rose-950/30 px-2.5 py-0.5 text-xs font-medium text-rose-700">
          <X className="h-3 w-3" /> Fallo
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 dark:bg-amber-950/30 px-2.5 py-0.5 text-xs font-medium text-amber-700">
          Pendiente
        </span>
      );
  }
}

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
      className="mt-3 flex w-full items-center justify-between gap-3 rounded-xl border border-violet-100 dark:border-violet-900/40 bg-violet-50/30 dark:bg-violet-950/20 px-3 py-2 text-left transition-colors hover:bg-violet-50/60 dark:hover:bg-violet-950/40"
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
  const [editSubject, setEditSubject] = useState("");
  const [editBody, setEditBody] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveResult, setSaveResult] = useState<"ok" | "error" | null>(null);
  const [sending, setSending] = useState(false);
  const [sendResult, setSendResult] = useState<{ ok: boolean; error?: string } | null>(null);
  const [generating, setGenerating] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [sendStatus, setSendStatus] = useState<ReplyAssistantSendStatusResponse | null>(null);
  const [pollingSendStatus, setPollingSendStatus] = useState(false);

  // Reset edit state when draft changes
  useEffect(() => {
    setIsEditing(false);
    setSaveResult(null);
    setSendResult(null);
  }, [draft?.id, draft?.updated_at]);

  function startEdit() {
    if (!draft) return;
    setEditSubject(draft.subject);
    setEditBody(draft.body);
    setIsEditing(true);
    setSaveResult(null);
  }

  function cancelEdit() {
    setIsEditing(false);
    setSaveResult(null);
  }

  async function handleSave() {
    if (!draft) return;
    setSaving(true);
    setSaveResult(null);
    try {
      await updateReplyAssistantDraft(messageId, {
        subject: editSubject,
        body: editBody,
        edited_by: "dashboard",
      });
      setSaveResult("ok");
      setIsEditing(false);
      await onRefresh();
    } catch {
      setSaveResult("error");
    } finally {
      setSaving(false);
    }
  }

  async function handleSend() {
    setSending(true);
    setSendResult(null);
    try {
      const result = await sendReplyAssistantDraft(messageId);
      if (result.status === "sent") {
        setSendResult({ ok: true });
      } else if (result.status === "failed") {
        setSendResult({ ok: false, error: result.error || "Error desconocido" });
      } else {
        // sending — poll for status
        setSendResult({ ok: true });
        void pollSendStatus();
      }
      await onRefresh();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "No se pudo enviar";
      setSendResult({ ok: false, error: msg });
    } finally {
      setSending(false);
    }
  }

  const pollSendStatus = useCallback(async () => {
    setPollingSendStatus(true);
    try {
      const status = await getReplyAssistantSendStatus(messageId);
      setSendStatus(status);
      if (status.latest_send?.status === "sending") {
        setTimeout(() => void pollSendStatus(), 3000);
      } else {
        setPollingSendStatus(false);
        await onRefresh();
      }
    } catch {
      setPollingSendStatus(false);
    }
  }, [messageId, onRefresh]);

  async function handleGenerate() {
    setGenerating(true);
    try {
      await generateReplyAssistantDraft(messageId);
      await onRefresh();
    } catch {
      // parent handles error display
    } finally {
      setGenerating(false);
    }
  }

  async function handleReview() {
    setReviewing(true);
    try {
      await requestReplyAssistantDraftReview(messageId);
      await onRefresh();
    } catch {
      // parent handles error display
    } finally {
      setReviewing(false);
    }
  }

  // Determine blocked reason — use draft field or send status
  const blockedReason = draft?.send_blocked_reason || sendStatus?.send_blocked_reason || null;
  const isAlreadySent = draft?.latest_send?.status === "sent";
  const isSendDisabled = sending || !!blockedReason || isAlreadySent || isEditing;

  // ─── Collapsed mode ─────────────────────────────────
  if (isCollapsed) {
    return <CollapsedSummary draft={draft} onExpand={() => setIsCollapsed(false)} />;
  }

  // ─── No draft yet ────────────────────────────────────
  if (!draft) {
    return (
      <div className={cn(
        "mt-3 rounded-2xl border border-violet-100 dark:border-violet-900/40 bg-violet-50/30 dark:bg-violet-950/20 p-4",
        compact && "p-3"
      )}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className={cn("text-sm font-medium text-foreground", compact && "text-xs")}>
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
        <p className="mt-2 text-sm text-muted-foreground">
          Todavía no hay draft sugerido para esta reply.
        </p>
      </div>
    );
  }

  // ─── Draft exists ────────────────────────────────────
  return (
    <div className={cn(
      "mt-3 rounded-2xl border border-violet-100 dark:border-violet-900/40 bg-violet-50/30 dark:bg-violet-950/20 p-4",
      compact && "p-3"
    )}>
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <p className={cn("text-sm font-medium text-foreground", compact && "text-xs")}>
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
              <span className="inline-flex items-center gap-1 rounded-full bg-sky-50 px-2.5 py-0.5 text-xs font-medium text-sky-700">
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

      {/* Meta line */}
      {!compact && (
        <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted-foreground">
          {draft.suggested_tone && <span>Tono: {draft.suggested_tone}</span>}
          <span>{draft.generator_role} · {draft.generator_model}</span>
          <span className="font-data"><RelativeTime date={draft.updated_at} /></span>
          {draft.edited_at && (
            <span className="font-data">
              Editado <RelativeTime date={draft.edited_at} />
              {draft.edited_by && <> por {draft.edited_by}</>}
            </span>
          )}
        </div>
      )}

      {/* Summary */}
      {draft.summary && !compact && (
        <p className="mt-3 text-sm text-foreground/80">{draft.summary}</p>
      )}

      {/* Subject/Body — edit or view */}
      <div className={cn("mt-3 rounded-xl bg-card/80 px-3 py-3 shadow-sm", compact && "mt-2")}>
        {isEditing ? (
          <div className="space-y-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-foreground/80">Asunto</label>
              <input
                type="text"
                value={editSubject}
                onChange={(e) => setEditSubject(e.target.value)}
                className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground outline-none focus:border-violet-300 focus:ring-1 focus:ring-violet-200"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-foreground/80">Cuerpo</label>
              <textarea
                value={editBody}
                onChange={(e) => setEditBody(e.target.value)}
                rows={compact ? 4 : 8}
                className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm leading-relaxed text-foreground outline-none focus:border-violet-300 focus:ring-1 focus:ring-violet-200"
              />
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                className="rounded-xl gap-1.5"
                onClick={() => void handleSave()}
                disabled={saving}
              >
                <Save className="h-3.5 w-3.5" />
                {saving ? "Guardando..." : "Guardar"}
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="rounded-xl"
                onClick={cancelEdit}
                disabled={saving}
              >
                Cancelar
              </Button>
              {saveResult === "ok" && (
                <span className="text-xs text-emerald-600 flex items-center gap-1">
                  <Check className="h-3 w-3" /> Guardado
                </span>
              )}
              {saveResult === "error" && (
                <span className="text-xs text-rose-600">Error al guardar</span>
              )}
            </div>
          </div>
        ) : (
          <>
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm font-medium text-foreground">{draft.subject}</p>
              {!isAlreadySent && (
                <button
                  onClick={startEdit}
                  className="shrink-0 rounded-lg p-1 text-muted-foreground hover:bg-muted hover:text-muted-foreground transition-colors"
                  title="Editar draft"
                >
                  <Edit3 className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
            <p className={cn(
              "mt-2 whitespace-pre-line text-sm leading-relaxed text-foreground/80",
              compact && "line-clamp-6"
            )}>
              {draft.body}
            </p>
          </>
        )}
      </div>

      {/* Blocked reason */}
      {blockedReason && (
        <div className="mt-3 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 dark:bg-amber-950/30 px-3 py-2 text-sm text-amber-800">
          <Lock className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{blockedReason}</span>
        </div>
      )}

      {/* Send result feedback */}
      {sendResult && !sendResult.ok && (
        <div className="mt-3 flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 dark:bg-rose-950/30 px-3 py-2 text-sm text-rose-700">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{sendResult.error}</span>
        </div>
      )}
      {sendResult?.ok && !isAlreadySent && (
        <div className="mt-3 flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 dark:bg-emerald-950/30 px-3 py-2 text-sm text-emerald-700">
          <Check className="mt-0.5 h-4 w-4 shrink-0" />
          <span>Envío iniciado correctamente</span>
        </div>
      )}

      {/* Send action */}
      {!isEditing && (
        <div className="mt-3 flex items-center gap-3">
          <Button
            size="sm"
            className={cn(
              "rounded-xl gap-1.5",
              isAlreadySent
                ? "bg-emerald-600 hover:bg-emerald-700"
                : "bg-violet-600 hover:bg-violet-700"
            )}
            onClick={() => void handleSend()}
            disabled={isSendDisabled}
          >
            {sending ? (
              <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Enviando...</>
            ) : isAlreadySent ? (
              <><Check className="h-3.5 w-3.5" /> Ya enviado</>
            ) : (
              <><Send className="h-3.5 w-3.5" /> Enviar respuesta</>
            )}
          </Button>
          {draft.latest_send?.sent_at && (
            <span className="text-xs text-muted-foreground font-data">
              Enviado <RelativeTime date={draft.latest_send.sent_at} />
            </span>
          )}
          {draft.latest_send?.error && (
            <span className="text-xs text-rose-600">{draft.latest_send.error}</span>
          )}
          {pollingSendStatus && (
            <span className="text-xs text-blue-600 flex items-center gap-1">
              <Loader2 className="h-3 w-3 animate-spin" /> Verificando estado...
            </span>
          )}
        </div>
      )}

      {/* Review section — only in full mode */}
      {!compact && draft.review && (
        <div className="mt-4 rounded-xl border border-fuchsia-100 bg-fuchsia-50/40 px-3 py-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-foreground">Review del draft</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {draft.review.reviewer_role || "reviewer"} ·{" "}
                {draft.review.reviewer_model || "modelo no informado"}
              </p>
            </div>
            <span className="rounded-full bg-card px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
              {draft.review.status}
            </span>
          </div>
          {draft.review.summary && (
            <p className="mt-3 text-sm text-foreground/80">{draft.review.summary}</p>
          )}
          {draft.review.feedback && (
            <p className="mt-2 text-sm text-muted-foreground">
              <span className="font-medium text-foreground/80">Feedback:</span>{" "}
              {draft.review.feedback}
            </p>
          )}
          {draft.review.recommended_action && (
            <p className="mt-2 text-sm text-muted-foreground">
              <span className="font-medium text-foreground/80">Acción recomendada:</span>{" "}
              {draft.review.recommended_action}
            </p>
          )}
          {draft.review.suggested_edits && draft.review.suggested_edits.length > 0 && (
            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
              {draft.review.suggested_edits.map((edit, index) => (
                <li key={`${draft.review?.id}-edit-${index}`}>{edit}</li>
              ))}
            </ul>
          )}
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            {draft.review.should_use_as_is && (
              <span className="rounded-full bg-emerald-50 dark:bg-emerald-950/30 px-2.5 py-0.5 font-medium text-emerald-700">
                Usable tal cual
              </span>
            )}
            {draft.review.should_edit && (
              <span className="rounded-full bg-amber-50 dark:bg-amber-950/30 px-2.5 py-0.5 font-medium text-amber-700">
                Conviene editar
              </span>
            )}
            {draft.review.should_escalate && (
              <span className="rounded-full bg-fuchsia-50 dark:bg-fuchsia-950/30 px-2.5 py-0.5 font-medium text-fuchsia-700">
                Mejor escalar
              </span>
            )}
          </div>
          {draft.review.error && (
            <p className="mt-2 text-sm text-rose-600">{draft.review.error}</p>
          )}
        </div>
      )}

      {/* Compact review summary */}
      {compact && draft.review && (
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
      )}
    </div>
  );
}

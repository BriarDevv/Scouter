"use client";

import { useCallback, useState } from "react";
import {
  AlertTriangle,
  Check,
  Loader2,
  Lock,
  Send,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { RelativeTime } from "@/components/shared/relative-time";
import {
  sendReplyAssistantDraft,
  getReplyAssistantSendStatus,
} from "@/lib/api/client";
import { cn } from "@/lib/utils";
import type { ReplyAssistantDraft, ReplyAssistantSendStatusResponse } from "@/types";

// ─── Send status badge ────────────────────────────────

export function SendStatusBadge({ draft }: { draft: ReplyAssistantDraft }) {
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

interface ReplyDraftSendStatusProps {
  messageId: string;
  draft: ReplyAssistantDraft;
  isEditing: boolean;
  onRefresh: () => void | Promise<void>;
}

// ─── Send status section ──────────────────────────────

export function ReplyDraftSendStatus({
  messageId,
  draft,
  isEditing,
  onRefresh,
}: ReplyDraftSendStatusProps) {
  const [sending, setSending] = useState(false);
  const [sendResult, setSendResult] = useState<{ ok: boolean; error?: string } | null>(null);
  const [sendStatus, setSendStatus] = useState<ReplyAssistantSendStatusResponse | null>(null);
  const [pollingSendStatus, setPollingSendStatus] = useState(false);

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
    } catch (err) {
      console.error("reply_draft_send_status_poll_failed", err);
      setPollingSendStatus(false);
    }
  }, [messageId, onRefresh]);

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

  const blockedReason = draft.send_blocked_reason || sendStatus?.send_blocked_reason || null;
  const isAlreadySent = draft.latest_send?.status === "sent";
  const isSendDisabled = sending || !!blockedReason || isAlreadySent || isEditing;

  return (
    <>
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
        <div className="mt-4 flex items-center gap-3">
          <Button
            size="sm"
            className={cn(
              "rounded-xl gap-1.5",
              isAlreadySent
                ? "bg-emerald-600 hover:bg-emerald-700"
                : "bg-foreground hover:bg-foreground/80"
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
    </>
  );
}

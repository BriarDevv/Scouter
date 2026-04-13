"use client";

import { useEffect, useState } from "react";
import { Check, Edit3, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { updateReplyAssistantDraft } from "@/lib/api/client";
import { cn } from "@/lib/utils";
import type { ReplyAssistantDraft } from "@/types";

// ─── Props ─────────────────────────────────────────────

interface ReplyDraftEditorProps {
  messageId: string;
  draft: ReplyAssistantDraft;
  compact: boolean;
  isEditing: boolean;
  onEditingChange: (editing: boolean) => void;
  onRefresh: () => void | Promise<void>;
}

// ─── Editor ───────────────────────────────────────────

export function ReplyDraftEditor({
  messageId,
  draft,
  compact,
  isEditing,
  onEditingChange,
  onRefresh,
}: ReplyDraftEditorProps) {
  const [editSubject, setEditSubject] = useState("");
  const [editBody, setEditBody] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveResult, setSaveResult] = useState<"ok" | "error" | null>(null);

  const isAlreadySent = draft.latest_send?.status === "sent";

  // Reset save result when draft changes
  useEffect(() => {
    setSaveResult(null);
  }, [draft.id, draft.updated_at]);

  function startEdit() {
    setEditSubject(draft.subject);
    setEditBody(draft.body);
    onEditingChange(true);
    setSaveResult(null);
  }

  function cancelEdit() {
    onEditingChange(false);
    setSaveResult(null);
  }

  async function handleSave() {
    setSaving(true);
    setSaveResult(null);
    try {
      await updateReplyAssistantDraft(messageId, {
        subject: editSubject,
        body: editBody,
        edited_by: "dashboard",
      });
      setSaveResult("ok");
      onEditingChange(false);
      await onRefresh();
    } catch (err) {
      console.error("reply_draft_save_failed", err);
      setSaveResult("error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className={cn("rounded-xl bg-card/80 px-4 py-4 shadow-sm", compact ? "mt-3" : "mt-4")}>
      {isEditing ? (
        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-foreground/80">Asunto</label>
            <input
              type="text"
              value={editSubject}
              onChange={(e) => setEditSubject(e.target.value)}
              className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground outline-none focus:border-ring focus:ring-1 focus:ring-ring/50"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-foreground/80">Cuerpo</label>
            <textarea
              value={editBody}
              onChange={(e) => setEditBody(e.target.value)}
              rows={compact ? 4 : 8}
              className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm leading-relaxed text-foreground outline-none focus:border-ring focus:ring-1 focus:ring-ring/50"
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
  );
}

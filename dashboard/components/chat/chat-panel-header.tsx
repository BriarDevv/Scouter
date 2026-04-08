"use client";

import { Menu, Plus, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface ChatPanelHeaderProps {
  title: string | null;
  showHistory: boolean;
  onToggleHistory: () => void;
  onNew: () => void;
  onClose: () => void;
}

export function ChatPanelHeader({
  title,
  showHistory,
  onToggleHistory,
  onNew,
  onClose,
}: ChatPanelHeaderProps) {
  return (
    <div className="flex items-center gap-2 border-b border-border px-3 py-2.5">
      <button
        onClick={onToggleHistory}
        className={cn(
          "rounded-lg p-1.5 transition-colors",
          showHistory
            ? "bg-muted dark:bg-muted text-foreground dark:text-foreground"
            : "text-muted-foreground hover:bg-muted hover:text-foreground"
        )}
        title="Historial de conversaciones"
      >
        <Menu className="h-4 w-4" />
      </button>
      <span className="flex-1 truncate text-sm font-semibold font-heading">
        {title || "Chat IA"}
      </span>
      <button
        onClick={onNew}
        className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
        title="Nueva conversación"
      >
        <Plus className="h-4 w-4" />
      </button>
      <button
        onClick={onClose}
        className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
        title="Cerrar chat"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

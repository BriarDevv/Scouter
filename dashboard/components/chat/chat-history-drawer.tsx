"use client";

import { motion } from "framer-motion";
import { MessageSquare, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ChatConversationSummary } from "@/types";

interface ChatHistoryDrawerProps {
  conversations: ChatConversationSummary[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  loading?: boolean;
}

export function ChatHistoryDrawer({
  conversations,
  activeId,
  onSelect,
  onDelete,
  loading,
}: ChatHistoryDrawerProps) {
  return (
    <motion.div
      initial={{ x: -280, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: -280, opacity: 0 }}
      transition={{ type: "spring", damping: 25, stiffness: 250 }}
      className="absolute inset-0 z-10 flex flex-col bg-card"
    >
      <div className="border-b border-border px-3 py-2.5">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
          Conversaciones
        </h3>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {loading ? (
          <div className="space-y-2 p-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-10 animate-pulse rounded-lg bg-muted" />
            ))}
          </div>
        ) : conversations.length === 0 ? (
          <p className="p-4 text-xs text-muted-foreground text-center">
            Sin conversaciones previas
          </p>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              className={cn(
                "group flex items-center gap-2 rounded-xl px-3 py-2 text-sm cursor-pointer transition-colors",
                activeId === conv.id
                  ? "bg-muted dark:bg-muted text-foreground dark:text-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
              onClick={() => onSelect(conv.id)}
            >
              <MessageSquare className="h-3.5 w-3.5 shrink-0" />
              <span className="flex-1 truncate text-xs">
                {conv.title || "Nueva conversación"}
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(conv.id);
                }}
                className="opacity-0 group-hover:opacity-100 rounded p-0.5 hover:bg-destructive/10 hover:text-destructive transition-all"
              >
                <Trash2 className="h-3 w-3" />
              </button>
            </div>
          ))
        )}
      </div>
    </motion.div>
  );
}

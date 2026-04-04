"use client";

import { useCallback, useEffect, useState } from "react";
import { useChat } from "@/lib/hooks/use-chat";
import {
  createConversation,
  deleteConversation,
  getConversation,
  listConversations,
} from "@/lib/api/client";
import { ChatMessages } from "@/components/chat/chat-messages";
import { ChatInput } from "@/components/chat/chat-input";
import { cn } from "@/lib/utils";
import {
  MessageSquarePlus,
  MessagesSquare,
  Sparkles,
  Trash2,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import type { ChatConversationSummary } from "@/types";

export default function ChatPage() {
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ChatConversationSummary[]>([]);
  const [currentTitle, setCurrentTitle] = useState<string | null>(null);
  const [historyOpen, setHistoryOpen] = useState(true);
  const [loadingList, setLoadingList] = useState(true);

  const { messages, isStreaming, error, sendMessage, setMessages } = useChat(activeConversationId);

  useEffect(() => {
    listConversations()
      .then(setConversations)
      .catch((err) => console.warn("Failed to load conversations:", err))
      .finally(() => setLoadingList(false));
  }, []);

  useEffect(() => {
    if (!activeConversationId) {
      setCurrentTitle(null);
      return;
    }
    getConversation(activeConversationId)
      .then((detail) => {
        setMessages(detail.messages);
        setCurrentTitle(detail.title);
      })
      .catch(() => {});
  }, [activeConversationId, setMessages]);

  const handleNew = useCallback(async () => {
    const conv = await createConversation();
    setConversations((prev) => [{
      id: conv.id, title: null, message_count: 0,
      last_message_at: null, created_at: conv.created_at,
    }, ...prev]);
    setActiveConversationId(conv.id);
    setMessages([]);
    setCurrentTitle(null);
  }, [setMessages]);

  const handleDelete = useCallback(async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    await deleteConversation(id);
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (activeConversationId === id) {
      setActiveConversationId(null);
      setMessages([]);
      setCurrentTitle(null);
    }
  }, [activeConversationId, setMessages]);

  const handleSend = useCallback(async (content: string) => {
    let targetId = activeConversationId;
    if (!targetId) {
      const conv = await createConversation();
      targetId = conv.id;
      setConversations((prev) => [{
        id: conv.id, title: null, message_count: 0,
        last_message_at: null, created_at: conv.created_at,
      }, ...prev]);
      setActiveConversationId(conv.id);
    }
    await sendMessage(content, targetId);
  }, [activeConversationId, sendMessage]);

  return (
    <div className="flex h-full overflow-hidden">
      {/* History panel */}
      <div className={cn(
        "flex flex-col shrink-0 border-r border-border/40 bg-muted/20 transition-all duration-300",
        historyOpen ? "w-60" : "w-0 overflow-hidden border-r-0"
      )}>
        <div className="flex items-center gap-2 px-3 py-3.5 border-b border-border/40 shrink-0">
          <MessagesSquare className="h-3.5 w-3.5 text-violet-500 shrink-0" />
          <span className="text-[11px] font-semibold font-heading text-muted-foreground uppercase tracking-wider flex-1">
            Conversaciones
          </span>
          <button
            onClick={() => void handleNew()}
            className="h-6 w-6 rounded-lg flex items-center justify-center text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            title="Nueva conversación"
          >
            <MessageSquarePlus className="h-3.5 w-3.5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
          {loadingList ? (
            <div className="space-y-1 p-1">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-8 rounded-lg bg-muted/60 animate-pulse" />
              ))}
            </div>
          ) : conversations.length === 0 ? (
            <p className="px-3 py-8 text-xs text-muted-foreground text-center">
              Sin conversaciones aún
            </p>
          ) : (
            conversations.map(conv => (
              <button
                key={conv.id}
                onClick={() => setActiveConversationId(conv.id)}
                className={cn(
                  "group w-full text-left rounded-xl px-3 py-2 transition-all flex items-center gap-2",
                  activeConversationId === conv.id
                    ? "bg-violet-50 dark:bg-violet-950/40 text-violet-700 dark:text-violet-300"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                <span className="flex-1 truncate text-xs font-medium">
                  {conv.title || "Nueva conversación"}
                </span>
                <span
                  role="button"
                  onClick={(e) => { void handleDelete(conv.id, e); }}
                  className="opacity-0 group-hover:opacity-100 h-4 w-4 shrink-0 flex items-center justify-center text-muted-foreground hover:text-destructive transition-all"
                >
                  <Trash2 className="h-3 w-3" />
                </span>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Main chat */}
      <div className="flex-1 flex flex-col min-w-0 relative">
        {/* Toggle handle */}
        <button
          onClick={() => setHistoryOpen(!historyOpen)}
          className="absolute left-0 top-1/2 -translate-y-1/2 z-10 h-10 w-4 rounded-r-lg bg-border/30 hover:bg-border/60 text-muted-foreground flex items-center justify-center transition-colors"
          title={historyOpen ? "Ocultar historial" : "Mostrar historial"}
        >
          {historyOpen
            ? <ChevronLeft className="h-3 w-3" />
            : <ChevronRight className="h-3 w-3" />
          }
        </button>

        {/* Header */}
        <div className="flex items-center gap-3 px-6 py-3.5 border-b border-border/40 shrink-0">
          <div className="h-7 w-7 rounded-lg bg-violet-100 dark:bg-violet-950/50 flex items-center justify-center shrink-0">
            <Sparkles className="h-3.5 w-3.5 text-violet-600 dark:text-violet-400" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold font-heading leading-none truncate">
              {currentTitle || "Mote"}
            </p>
            {!currentTitle && (
              <p className="text-xs text-muted-foreground mt-0.5">Agente IA · Scouter</p>
            )}
          </div>
          <button
            onClick={() => void handleNew()}
            className="ml-auto flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors shrink-0"
          >
            <MessageSquarePlus className="h-3.5 w-3.5" />
            Nueva
          </button>
        </div>

        {/* Messages */}
        <ChatMessages messages={messages} isStreaming={isStreaming} />

        {/* Input */}
        <ChatInput onSend={handleSend} disabled={isStreaming} error={error} />
      </div>
    </div>
  );
}

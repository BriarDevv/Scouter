"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus, MessageSquare, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  createConversation,
  deleteConversation,
  getConversation,
  listConversations,
} from "@/lib/api/client";
import { useChat } from "@/lib/hooks/use-chat";
import { ChatMessages } from "@/components/chat/chat-messages";
import { ChatInput } from "@/components/chat/chat-input";
import type { ChatConversationSummary } from "@/types";

export default function ChatPage() {
  const [conversations, setConversations] = useState<ChatConversationSummary[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const { messages, isStreaming, error, sendMessage, setMessages } = useChat(activeId);

  // Load conversation list
  useEffect(() => {
    listConversations()
      .then(setConversations)
      .catch(() => {})
      .finally(() => setLoadingList(false));
  }, []);

  // Load messages when active conversation changes
  useEffect(() => {
    if (!activeId) return;
    getConversation(activeId)
      .then(detail => setMessages(detail.messages))
      .catch(() => {});
  }, [activeId, setMessages]);

  const handleNew = useCallback(async () => {
    const conv = await createConversation();
    setConversations(prev => [
      {
        id: conv.id,
        title: null,
        message_count: 0,
        last_message_at: null,
        created_at: conv.created_at,
      },
      ...prev,
    ]);
    setActiveId(conv.id);
    setMessages([]);
  }, [setMessages]);

  const handleDelete = useCallback(
    async (id: string) => {
      await deleteConversation(id);
      setConversations(prev => prev.filter(c => c.id !== id));
      if (activeId === id) {
        setActiveId(null);
        setMessages([]);
      }
    },
    [activeId, setMessages]
  );

  return (
    <div className="flex h-[calc(100vh-2rem)] gap-0 overflow-hidden rounded-2xl border border-border bg-card">
      {/* Conversation sidebar */}
      <div className="flex w-[280px] flex-col border-r border-border bg-muted/30">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <h2 className="text-sm font-semibold">Conversaciones</h2>
          <button
            onClick={handleNew}
            className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            <Plus className="h-4 w-4" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {loadingList ? (
            <div className="space-y-2 p-2">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-12 animate-pulse rounded-lg bg-muted" />
              ))}
            </div>
          ) : conversations.length === 0 ? (
            <p className="p-4 text-xs text-muted-foreground text-center">
              Sin conversaciones. Hace click en + para iniciar una.
            </p>
          ) : (
            conversations.map(conv => (
              <div
                key={conv.id}
                className={cn(
                  "group flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm cursor-pointer transition-colors",
                  activeId === conv.id
                    ? "bg-violet-50 dark:bg-violet-950/40 text-violet-700 dark:text-violet-300"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
                onClick={() => setActiveId(conv.id)}
              >
                <MessageSquare className="h-4 w-4 shrink-0" />
                <span className="flex-1 truncate">
                  {conv.title || "Nueva conversacion"}
                </span>
                <button
                  onClick={e => {
                    e.stopPropagation();
                    handleDelete(conv.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 rounded p-0.5 hover:bg-destructive/10 hover:text-destructive transition-all"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Chat area */}
      <div className="flex flex-1 flex-col">
        {activeId ? (
          <>
            <ChatMessages messages={messages} isStreaming={isStreaming} />
            <ChatInput onSend={sendMessage} disabled={isStreaming} error={error} />
          </>
        ) : (
          <div className="flex flex-1 items-center justify-center">
            <div className="text-center space-y-3">
              <MessageSquare className="h-12 w-12 mx-auto text-muted-foreground/40" />
              <p className="text-muted-foreground text-sm">
                Selecciona una conversacion o crea una nueva
              </p>
              <button
                onClick={handleNew}
                className="inline-flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 transition-colors"
              >
                <Plus className="h-4 w-4" />
                Nueva conversacion
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

"use client";

import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useChatPanel } from "@/lib/hooks/use-chat-panel";
import { useChat } from "@/lib/hooks/use-chat";
import {
  createConversation,
  deleteConversation,
  getConversation,
  listConversations,
} from "@/lib/api/client";
import { ChatMessages } from "@/components/chat/chat-messages";
import { ChatInput } from "@/components/chat/chat-input";
import { ChatPanelHeader } from "@/components/chat/chat-panel-header";
import { ChatHistoryDrawer } from "@/components/chat/chat-history-drawer";
import type { ChatConversationSummary } from "@/types";

export function ChatPanel() {
  const {
    isOpen,
    close,
    activeConversationId,
    setActiveConversationId,
  } = useChatPanel();

  const { messages, isStreaming, error, sendMessage, setMessages } =
    useChat(activeConversationId);

  const [conversations, setConversations] = useState<ChatConversationSummary[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [loadingList, setLoadingList] = useState(true);
  const [currentTitle, setCurrentTitle] = useState<string | null>(null);

  // Load conversation list when panel opens
  useEffect(() => {
    if (!isOpen) return;
    listConversations()
      .then(setConversations)
      .catch(() => {})
      .finally(() => setLoadingList(false));
  }, [isOpen]);

  // Load messages when active conversation changes. The null-case cleanup
  // is a legitimate setState — clearing title when no conversation is active.
  useEffect(() => {
    if (!activeConversationId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
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
    setConversations((prev) => [
      {
        id: conv.id,
        title: null,
        message_count: 0,
        last_message_at: null,
        created_at: conv.created_at,
      },
      ...prev,
    ]);
    setActiveConversationId(conv.id);
    setMessages([]);
    setCurrentTitle(null);
    setShowHistory(false);
  }, [setActiveConversationId, setMessages]);

  const handleDelete = useCallback(
    async (id: string) => {
      await deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeConversationId === id) {
        setActiveConversationId(null);
        setMessages([]);
        setCurrentTitle(null);
      }
    },
    [activeConversationId, setActiveConversationId, setMessages]
  );

  const handleSelectConversation = useCallback(
    (id: string) => {
      setActiveConversationId(id);
      setShowHistory(false);
    },
    [setActiveConversationId]
  );

  // Auto-create conversation on first message if none active
  const handleSend = useCallback(
    async (content: string) => {
      let targetId = activeConversationId;
      if (!targetId) {
        const conv = await createConversation();
        targetId = conv.id;
        setConversations((prev) => [
          {
            id: conv.id,
            title: null,
            message_count: 0,
            last_message_at: null,
            created_at: conv.created_at,
          },
          ...prev,
        ]);
        setActiveConversationId(conv.id);
      }
      await sendMessage(content, targetId);
    },
    [activeConversationId, setActiveConversationId, sendMessage]
  );

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ x: 400, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 400, opacity: 0 }}
          transition={{ type: "spring", damping: 25, stiffness: 200 }}
          className="fixed inset-y-0 right-0 z-30 flex w-[400px] flex-col border-l border-border bg-card shadow-md"
        >
          <ChatPanelHeader
            title={currentTitle}
            showHistory={showHistory}
            onToggleHistory={() => setShowHistory(!showHistory)}
            onNew={handleNew}
            onClose={close}
          />

          <div className="relative flex flex-1 overflow-hidden">
            {/* History drawer */}
            <AnimatePresence>
              {showHistory && (
                <ChatHistoryDrawer
                  conversations={conversations}
                  activeId={activeConversationId}
                  onSelect={handleSelectConversation}
                  onDelete={handleDelete}
                  loading={loadingList}
                />
              )}
            </AnimatePresence>

            {/* Chat content */}
            <div className="flex flex-1 flex-col">
              <ChatMessages messages={messages} isStreaming={isStreaming} />
              <ChatInput
                onSend={handleSend}
                disabled={isStreaming}
                error={error}
              />
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

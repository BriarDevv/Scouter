"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

interface ChatPanelState {
  isOpen: boolean;
  toggle: () => void;
  open: () => void;
  close: () => void;
  activeConversationId: string | null;
  setActiveConversationId: (id: string | null) => void;
}

const ChatPanelContext = createContext<ChatPanelState | null>(null);

const STORAGE_KEY = "clawscout-chat-open";

export function ChatPanelProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);

  // Restore from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === "true") setIsOpen(true);
    } catch {
      // SSR or localStorage unavailable
    }
  }, []);

  // Persist to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, String(isOpen));
    } catch {
      // Ignore
    }
  }, [isOpen]);

  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);
  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);

  return (
    <ChatPanelContext value={{
      isOpen,
      toggle,
      open,
      close,
      activeConversationId,
      setActiveConversationId,
    }}>
      {children}
    </ChatPanelContext>
  );
}

export function useChatPanel(): ChatPanelState {
  const ctx = useContext(ChatPanelContext);
  if (!ctx) throw new Error("useChatPanel must be used within ChatPanelProvider");
  return ctx;
}

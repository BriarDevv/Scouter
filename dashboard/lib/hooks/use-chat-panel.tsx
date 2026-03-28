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
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
}

const ChatPanelContext = createContext<ChatPanelState | null>(null);

const CHAT_STORAGE_KEY = "clawscout-chat-open";
const SIDEBAR_STORAGE_KEY = "clawscout-sidebar-collapsed";

export function ChatPanelProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);

  // Restore from localStorage on mount
  useEffect(() => {
    try {
      if (localStorage.getItem(CHAT_STORAGE_KEY) === "true") setIsOpen(true);
      if (localStorage.getItem(SIDEBAR_STORAGE_KEY) === "true") setSidebarCollapsed(true);
    } catch {
      // SSR or localStorage unavailable
    }
  }, []);

  // Persist to localStorage
  useEffect(() => {
    try { localStorage.setItem(CHAT_STORAGE_KEY, String(isOpen)); } catch {}
  }, [isOpen]);

  useEffect(() => {
    try { localStorage.setItem(SIDEBAR_STORAGE_KEY, String(sidebarCollapsed)); } catch {}
  }, [sidebarCollapsed]);

  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);
  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggleSidebar = useCallback(() => setSidebarCollapsed((prev) => !prev), []);

  return (
    <ChatPanelContext value={{
      isOpen,
      toggle,
      open,
      close,
      activeConversationId,
      setActiveConversationId,
      sidebarCollapsed,
      toggleSidebar,
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

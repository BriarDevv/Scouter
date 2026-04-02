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
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    if (typeof window === "undefined") return false;
    return document.documentElement.classList.contains("sidebar-collapsed");
  });
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      if (localStorage.getItem(CHAT_STORAGE_KEY) === "true") setIsOpen(true);
    } catch {}
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    try { localStorage.setItem(CHAT_STORAGE_KEY, String(isOpen)); } catch {}
  }, [isOpen, hydrated]);

  useEffect(() => {
    if (!hydrated) return;
    try { localStorage.setItem(SIDEBAR_STORAGE_KEY, String(sidebarCollapsed)); } catch {}
  }, [sidebarCollapsed, hydrated]);

  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);
  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggleSidebar = useCallback(() => setSidebarCollapsed((prev) => !prev), []);

  return (
    <ChatPanelContext value={{
      isOpen, toggle, open, close,
      activeConversationId, setActiveConversationId,
      sidebarCollapsed, toggleSidebar,
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

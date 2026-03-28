"use client";

import { useChatPanel } from "@/lib/hooks/use-chat-panel";
import { cn } from "@/lib/utils";

export function LayoutShell({ children }: { children: React.ReactNode }) {
  const { isOpen, sidebarCollapsed } = useChatPanel();

  return (
    <main
      className={cn(
        "fixed inset-y-0 right-0 rounded-l-2xl border-l border-border/40 bg-background overflow-y-auto transition-all duration-300 ease-in-out",
        sidebarCollapsed ? "left-[68px]" : "left-64",
        isOpen ? "right-[400px]" : "right-0"
      )}
    >
      <div className="mx-auto max-w-[1400px] px-8 py-8">{children}</div>
    </main>
  );
}

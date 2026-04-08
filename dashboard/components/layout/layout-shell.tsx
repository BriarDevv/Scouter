"use client";

import { useChatPanel } from "@/lib/hooks/use-chat-panel";
import { cn } from "@/lib/utils";

export function LayoutShell({ children }: { children: React.ReactNode }) {
  const { sidebarCollapsed } = useChatPanel();

  return (
    <main
      className={cn(
        "fixed inset-y-0 right-0 flex flex-col bg-sidebar pt-2 pr-2 pb-2",
        "transition-[left] duration-[350ms] ease-in-out",
        sidebarCollapsed ? "left-[52px]" : "left-52",
      )}
    >
      <div className="flex-1 flex flex-col overflow-hidden rounded-xl border border-border/40 bg-background">
        {children}
      </div>
    </main>
  );
}

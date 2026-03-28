"use client";

import { useChatPanel } from "@/lib/hooks/use-chat-panel";
import { cn } from "@/lib/utils";

export function LayoutShell({ children }: { children: React.ReactNode }) {
  const { isOpen, sidebarCollapsed } = useChatPanel();

  return (
    <main
      className={cn(
        "min-h-screen transition-all duration-300 ease-in-out",
        sidebarCollapsed ? "ml-[68px]" : "ml-64",
        isOpen ? "mr-[400px]" : "mr-0"
      )}
    >
      <div className="mx-auto max-w-[1400px] px-8 py-8">{children}</div>
    </main>
  );
}

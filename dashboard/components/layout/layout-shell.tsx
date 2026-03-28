"use client";

import { useChatPanel } from "@/lib/hooks/use-chat-panel";
import { cn } from "@/lib/utils";

export function LayoutShell({ children }: { children: React.ReactNode }) {
  const { isOpen } = useChatPanel();

  return (
    <main
      className={cn(
        "ml-64 min-h-screen transition-all duration-300 ease-in-out",
        isOpen ? "mr-[400px]" : "mr-0"
      )}
    >
      <div className="mx-auto max-w-[1400px] px-8 py-8">{children}</div>
    </main>
  );
}

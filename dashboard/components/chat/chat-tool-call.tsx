"use client";

import { useState } from "react";
import { ChevronDown, Wrench, Loader2, CheckCircle2, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ChatToolCall } from "@/types";

const STATUS_ICONS = {
  running: Loader2,
  completed: CheckCircle2,
  failed: XCircle,
  pending: Loader2,
} as const;

const STATUS_COLORS = {
  running: "text-amber-500",
  completed: "text-emerald-500",
  failed: "text-destructive",
  pending: "text-muted-foreground",
} as const;

export function ChatToolCallCard({ toolCall }: { toolCall: ChatToolCall }) {
  const [expanded, setExpanded] = useState(false);
  const StatusIcon =
    STATUS_ICONS[toolCall.status as keyof typeof STATUS_ICONS] || Wrench;
  const statusColor =
    STATUS_COLORS[toolCall.status as keyof typeof STATUS_COLORS] || "";

  return (
    <div className="rounded-xl border border-border/50 bg-background/50 text-foreground">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 px-3 py-2 text-xs"
      >
        <Wrench className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="font-medium">{toolCall.tool_name}</span>
        <StatusIcon
          className={cn(
            "h-3.5 w-3.5 ml-auto",
            statusColor,
            toolCall.status === "running" && "animate-spin"
          )}
        />
        {toolCall.duration_ms !== null && (
          <span className="text-muted-foreground">{toolCall.duration_ms}ms</span>
        )}
        <ChevronDown
          className={cn(
            "h-3.5 w-3.5 text-muted-foreground transition-transform",
            expanded && "rotate-180"
          )}
        />
      </button>
      {expanded && (
        <div className="border-t border-border/50 px-3 py-2 text-xs space-y-2">
          {toolCall.arguments && (
            <div>
              <p className="font-medium text-muted-foreground mb-1">Argumentos:</p>
              <pre className="overflow-x-auto rounded bg-muted p-2 text-[11px]">
                {JSON.stringify(toolCall.arguments, null, 2)}
              </pre>
            </div>
          )}
          {toolCall.result && (
            <div>
              <p className="font-medium text-muted-foreground mb-1">Resultado:</p>
              <pre className="overflow-x-auto rounded bg-muted p-2 text-[11px] max-h-[200px]">
                {JSON.stringify(toolCall.result, null, 2)}
              </pre>
            </div>
          )}
          {toolCall.error && (
            <p className="text-destructive">Error: {toolCall.error}</p>
          )}
        </div>
      )}
    </div>
  );
}

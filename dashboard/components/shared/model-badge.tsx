"use client";

import { cn } from "@/lib/utils";
import { formatModelShort } from "@/lib/task-utils";

export function ModelBadge({ model, size = "sm" }: { model: string | null; size?: "sm" | "md" }) {
  if (!model) return null;
  if (model === "_system") {
    return (
      <span
        className={cn(
          "inline-flex items-center rounded font-bold font-data leading-tight",
          size === "md" ? "px-1.5 py-0.5 text-[10px]" : "px-1 py-px text-[9px]",
          "bg-zinc-100 dark:bg-zinc-800/60 text-zinc-500 dark:text-zinc-400"
        )}
        title="Sistema (sin LLM)"
      >
        SIS
      </span>
    );
  }
  const short = formatModelShort(model);
  const isReviewer = model.includes("27b") || model.includes("14b");
  return (
    <span
      className={cn(
        "inline-flex items-center rounded font-bold font-data leading-tight",
        size === "md" ? "px-1.5 py-0.5 text-[10px]" : "px-1 py-px text-[9px]",
        isReviewer
          ? "bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300"
          : "bg-cyan-50 dark:bg-cyan-950/40 text-cyan-700 dark:text-cyan-300"
      )}
      title={model}
    >
      {short}
    </span>
  );
}

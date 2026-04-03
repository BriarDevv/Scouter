"use client";

import { Loader2, Play, Square } from "lucide-react";
import { cn } from "@/lib/utils";

interface PipelineControlsProps {
  pipelineStatus: "idle" | "running" | "done" | "error" | "stopping";
  pipelineProgress: string | null;
  celeryOk: boolean;
  onStart: () => void;
  onStop: () => void;
}

export function PipelineControls({
  pipelineStatus,
  pipelineProgress,
  celeryOk,
  onStart,
  onStop,
}: PipelineControlsProps) {
  return (
    <div className="pt-1 space-y-1.5">
      {pipelineStatus !== "running" && pipelineStatus !== "stopping" ? (
        <button
          onClick={onStart}
          disabled={!celeryOk}
          className={cn(
            "flex w-full items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition-all",
            celeryOk
              ? "bg-violet-600 text-white hover:bg-violet-700 active:scale-[0.98]"
              : "bg-muted text-muted-foreground cursor-not-allowed"
          )}
        >
          <Play className="h-4 w-4" />
          Iniciar Pipeline
        </button>
      ) : (
        <button
          onClick={onStop}
          disabled={pipelineStatus === "stopping"}
          className={cn(
            "flex w-full items-center justify-center gap-2 rounded-xl bg-red-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-red-700 active:scale-[0.98] transition-all",
            pipelineStatus === "stopping" && "opacity-70"
          )}
        >
          <Square className="h-4 w-4" />
          {pipelineStatus === "stopping" ? "Deteniendo..." : "Detener Pipeline"}
        </button>
      )}
      {!celeryOk && (
        <p className="text-[10px] text-amber-500 text-center">
          Celery debe estar corriendo
        </p>
      )}
      {pipelineProgress && (
        <p className={cn(
          "text-[10px] text-center",
          pipelineStatus === "running" ? "text-violet-500" : pipelineStatus === "done" ? "text-emerald-500" : "text-muted-foreground"
        )}>
          {pipelineStatus === "running" && <Loader2 className="inline h-3 w-3 animate-spin mr-1" />}
          {pipelineProgress}
        </p>
      )}
    </div>
  );
}

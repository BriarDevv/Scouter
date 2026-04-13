"use client";

import { Loader2, Play, Square } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export type PipelineStatus = "idle" | "running" | "done" | "error" | "stopping";

interface PipelineControlsProps {
  pipelineStatus: PipelineStatus;
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
  const isRunning = pipelineStatus === "running" || pipelineStatus === "stopping";

  return (
    <div className="space-y-2">
      {!isRunning ? (
        <Button
          onClick={onStart}
          disabled={!celeryOk}
          size="lg"
          className="w-full rounded-xl"
        >
          <Play className="h-4 w-4" />
          Iniciar Pipeline
        </Button>
      ) : (
        <Button
          variant="destructive-solid"
          onClick={onStop}
          disabled={pipelineStatus === "stopping"}
          size="lg"
          className="w-full rounded-xl"
        >
          <Square className="h-3.5 w-3.5" />
          {pipelineStatus === "stopping" ? "Deteniendo..." : "Detener"}
        </Button>
      )}
      {pipelineProgress && (
        <div className="flex items-center gap-2">
          {isRunning && <Loader2 className="h-3 w-3 animate-spin text-muted-foreground shrink-0" />}
          <span className={cn(
            "text-[10px] font-medium truncate font-data",
            pipelineStatus === "done" ? "text-emerald-600 dark:text-emerald-400" : "text-muted-foreground"
          )}>
            {pipelineProgress}
          </span>
        </div>
      )}
    </div>
  );
}

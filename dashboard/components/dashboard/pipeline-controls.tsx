"use client";

import { Loader2, Play, Square } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

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
          className={cn("w-full rounded-xl", pipelineStatus === "stopping" && "opacity-70")}
        >
          <Square className="h-4 w-4" />
          {pipelineStatus === "stopping" ? "Deteniendo..." : "Detener Pipeline"}
        </Button>
      )}
      {!celeryOk && (
        <p className="text-[10px] text-amber-500 text-center">
          Celery debe estar corriendo
        </p>
      )}
      {pipelineProgress && (
        <p className={cn(
          "text-[10px] text-center",
          pipelineStatus === "running" ? "text-foreground" : pipelineStatus === "done" ? "text-emerald-500" : "text-muted-foreground"
        )}>
          {pipelineStatus === "running" && <Loader2 className="inline h-3 w-3 animate-spin mr-1" />}
          {pipelineProgress}
        </p>
      )}
    </div>
  );
}

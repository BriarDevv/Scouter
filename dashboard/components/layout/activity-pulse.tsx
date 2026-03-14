"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { getTasks } from "@/lib/api/client";
import type { TaskStatusRecord } from "@/types";
import {
  BrainCircuit,
  Search,
  BarChart3,
  Sparkles,
  FileText,
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
  ChevronRight,
} from "lucide-react";

const POLL_INTERVAL = 4_000;

const STEP_CONFIG: Record<string, { label: string; icon: typeof BrainCircuit }> = {
  pipeline_dispatch: { label: "Iniciando pipeline", icon: BrainCircuit },
  enrichment:        { label: "Enriqueciendo",      icon: Search },
  scoring:           { label: "Puntuando",           icon: BarChart3 },
  analysis:          { label: "Analizando con IA",   icon: Sparkles },
  draft_generation:  { label: "Generando draft",     icon: FileText },
  lead_review:       { label: "Review de lead",      icon: Sparkles },
  draft_review:      { label: "Review de draft",     icon: Sparkles },
  inbound_reply_review:  { label: "Clasificando reply",   icon: Sparkles },
  reply_draft_review:    { label: "Generando respuesta",  icon: FileText },
  completed:         { label: "Completado",          icon: CheckCircle2 },
};

function getStepConfig(step: string | null | undefined) {
  if (!step) return { label: "Procesando", icon: BrainCircuit };
  return STEP_CONFIG[step] ?? { label: step.replace(/_/g, " "), icon: BrainCircuit };
}

const STATUS_COLORS: Record<string, string> = {
  running:   "text-violet-500",
  started:   "text-violet-500",
  queued:    "text-amber-500",
  pending:   "text-amber-500",
  succeeded: "text-emerald-500",
  success:   "text-emerald-500",
  failed:    "text-red-500",
  retrying:  "text-amber-500",
};

function isActive(status: string) {
  return ["running", "started", "queued", "pending", "retrying"].includes(status);
}

function TaskRow({ task }: { task: TaskStatusRecord }) {
  const step = getStepConfig(task.current_step);
  const StepIcon = step.icon;
  const active = isActive(task.status);
  const failed = task.status === "failed";
  const done = ["succeeded", "success"].includes(task.status);

  return (
    <div className="flex items-start gap-2.5 py-1.5 group">
      <div className="relative mt-0.5 shrink-0">
        {active ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin text-violet-500" />
        ) : failed ? (
          <XCircle className="h-3.5 w-3.5 text-red-500" />
        ) : done ? (
          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
        ) : (
          <Clock className="h-3.5 w-3.5 text-muted-foreground" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <p className={cn(
          "text-xs font-medium truncate",
          active ? "text-sidebar-foreground" : "text-muted-foreground"
        )}>
          {step.label}
        </p>
        {task.lead_id && (
          <Link
            href={`/leads/${task.lead_id}`}
            className="text-[10px] text-muted-foreground/70 hover:text-violet-400 truncate block transition-colors"
          >
            {task.lead_id.slice(0, 8)}...
          </Link>
        )}
        {task.error && (
          <p className="text-[10px] text-red-400 truncate" title={task.error}>
            {task.error.slice(0, 50)}
          </p>
        )}
      </div>
    </div>
  );
}

export function ActivityPulse() {
  const [tasks, setTasks] = useState<TaskStatusRecord[]>([]);
  const [expanded, setExpanded] = useState(true);

  const poll = useCallback(async () => {
    try {
      const result = await getTasks({ limit: 10 });
      setTasks(result);
    } catch {
      // silent — sidebar shouldn't break on API errors
    }
  }, []);

  useEffect(() => {
    poll();
    const id = setInterval(poll, POLL_INTERVAL);
    return () => clearInterval(id);
  }, [poll]);

  const activeTasks = tasks.filter((t) => isActive(t.status));
  const recentDone = tasks.filter((t) => !isActive(t.status)).slice(0, 3);
  const displayTasks = expanded ? [...activeTasks, ...recentDone] : activeTasks;
  const hasActive = activeTasks.length > 0;

  if (tasks.length === 0) {
    return (
      <div className="px-3 py-3">
        <div className="flex items-center gap-2 px-1">
          <BrainCircuit className="h-4 w-4 text-muted-foreground/50" />
          <span className="text-[11px] font-medium text-muted-foreground/50">Sin actividad IA</span>
        </div>
      </div>
    );
  }

  return (
    <div className="px-3 py-3">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between px-1 mb-1 group"
      >
        <div className="flex items-center gap-2">
          <div className="relative">
            <BrainCircuit className={cn(
              "h-4 w-4",
              hasActive ? "text-violet-500" : "text-muted-foreground"
            )} />
            {hasActive && (
              <span className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-violet-500 animate-pulse" />
            )}
          </div>
          <span className={cn(
            "text-[11px] font-semibold uppercase tracking-wider",
            hasActive ? "text-sidebar-foreground" : "text-muted-foreground"
          )}>
            IA {hasActive ? `· ${activeTasks.length} activa${activeTasks.length > 1 ? "s" : ""}` : "· Idle"}
          </span>
        </div>
        <ChevronRight className={cn(
          "h-3 w-3 text-muted-foreground transition-transform",
          expanded && "rotate-90"
        )} />
      </button>

      {displayTasks.length > 0 && (
        <div className="space-y-0.5 pl-1">
          {displayTasks.map((task) => (
            <TaskRow key={task.task_id} task={task} />
          ))}
        </div>
      )}
    </div>
  );
}

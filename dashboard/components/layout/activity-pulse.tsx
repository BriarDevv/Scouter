"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { getTasks, getLLMSettings, getBatchPipelineStatus } from "@/lib/api/client";
import type { BatchPipelineProgress } from "@/lib/api/client";
import type { TaskStatusRecord, LLMSettings } from "@/types";
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

const REVIEWER_STEPS = new Set(["lead_review", "draft_review"]);
const NO_LLM_STEPS = new Set(["enrichment", "scoring", "pipeline_dispatch", "completed"]);

function getStepConfig(step: string | null | undefined) {
  if (!step) return { label: "Procesando", icon: BrainCircuit };
  return STEP_CONFIG[step] ?? { label: step.replace(/_/g, " "), icon: BrainCircuit };
}

function getModelForStep(step: string | null | undefined, llm: LLMSettings | null): string | null {
  if (!step) return null;
  if (NO_LLM_STEPS.has(step)) return "_system";
  if (!llm) return null;
  if (REVIEWER_STEPS.has(step)) return llm.reviewer_model;
  return llm.executor_model;
}

function formatModelShort(model: string): string {
  // "qwen3.5:9b" → "9B", "qwen3.5:27b" → "27B"
  const match = model.match(/:(\d+[bB])/);
  if (match) return match[1].toUpperCase();
  return model.split(":").pop()?.toUpperCase() || model;
}

function isActive(status: string) {
  return ["running", "started", "queued", "pending", "retrying"].includes(status);
}

function ModelBadge({ model }: { model: string | null }) {
  if (!model) return null;
  if (model === "_system") {
    return (
      <span className="inline-flex items-center rounded px-1 py-px text-[9px] font-bold font-data leading-tight bg-zinc-100 dark:bg-zinc-800/60 text-zinc-500 dark:text-zinc-400">
        SIS
      </span>
    );
  }
  const short = formatModelShort(model);
  const isReviewer = model.includes("27b") || model.includes("14b");
  return (
    <span className={cn(
      "inline-flex items-center rounded px-1 py-px text-[9px] font-bold font-data leading-tight",
      isReviewer
        ? "bg-amber-100 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300"
        : "bg-cyan-100 dark:bg-cyan-950/40 text-cyan-700 dark:text-cyan-300"
    )}>
      {short}
    </span>
  );
}

function TaskRow({ task, llm }: { task: TaskStatusRecord; llm: LLMSettings | null }) {
  const step = getStepConfig(task.current_step);
  const active = isActive(task.status);
  const stale = task.status === "stale";
  const failed = task.status === "failed" || stale;
  const done = ["succeeded", "success"].includes(task.status);
  const model = getModelForStep(task.current_step, llm);

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
        <div className="flex items-center gap-1.5">
          <p className={cn(
            "text-xs font-medium truncate",
            active ? "text-sidebar-foreground" : "text-muted-foreground"
          )}>
            {step.label}
          </p>
          <ModelBadge model={model} />
        </div>
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

const PULSE_STORAGE_KEY = "clawscout-activity-expanded";

export function ActivityPulse() {
  const [tasks, setTasks] = useState<TaskStatusRecord[]>([]);
  const [llm, setLlm] = useState<LLMSettings | null>(null);
  const [batch, setBatch] = useState<BatchPipelineProgress | null>(null);
  const [expanded, setExpanded] = useState(() => {
    try {
      const stored = localStorage.getItem(PULSE_STORAGE_KEY);
      return stored !== "false";
    } catch {
      return true;
    }
  });

  const toggleExpanded = useCallback(() => {
    setExpanded((prev) => {
      const next = !prev;
      try { localStorage.setItem(PULSE_STORAGE_KEY, String(next)); } catch {}
      return next;
    });
  }, []);

  const poll = useCallback(async () => {
    try {
      const [result, batchStatus] = await Promise.all([
        getTasks({ limit: 10 }),
        getBatchPipelineStatus(),
      ]);
      setTasks(result);
      setBatch(batchStatus);
    } catch {
      // silent — sidebar shouldn't break on API errors
    }
  }, []);

  useEffect(() => {
    poll();
    getLLMSettings().then(setLlm).catch(() => {});
    const id = setInterval(poll, POLL_INTERVAL);
    return () => clearInterval(id);
  }, [poll]);

  const activeTasksRaw = tasks.filter((t) => isActive(t.status));
  // Dedup: keep only the most recent task per lead_id + current_step
  const seenActive = new Set<string>();
  const activeTasks = activeTasksRaw.filter((t) => {
    const key = (t.lead_id ?? "no-lead") + ":" + (t.current_step ?? "no-step");
    if (seenActive.has(key)) return false;
    seenActive.add(key);
    return true;
  });
  // Dedup recent/stale tasks too — keep only the most recent per lead_id + current_step
  const seenDone = new Set<string>();
  const recentDone = tasks.filter((t) => {
    if (isActive(t.status)) return false;
    const key = (t.lead_id ?? "no-lead") + ":" + (t.current_step ?? "no-step");
    if (seenDone.has(key)) return false;
    seenDone.add(key);
    return true;
  }).slice(0, 3);
  const batchRunning = batch?.status === "running";
  const hasActive = activeTasks.length > 0 || batchRunning;
  const latestTask = activeTasks[0] ?? recentDone[0] ?? null;

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
        onClick={toggleExpanded}
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
            IA {batchRunning
              ? `· Pipeline ${batch!.processed ?? 0}/${batch!.total ?? 0}`
              : hasActive
                ? `· ${activeTasks.length} activa${activeTasks.length > 1 ? "s" : ""}`
                : "· Idle"}
          </span>
        </div>
        <ChevronRight className={cn(
          "h-3 w-3 text-muted-foreground transition-transform",
          expanded && "rotate-90"
        )} />
      </button>

      {expanded ? (
        <>
          {batchRunning && (
            <div className="mb-1.5 rounded-lg bg-violet-500/10 border border-violet-500/20 px-2.5 py-2 ml-1">
              <div className="flex items-center gap-2">
                <Loader2 className="h-3.5 w-3.5 animate-spin text-violet-500" />
                <div className="min-w-0 flex-1">
                  <p className="text-[11px] font-semibold text-violet-400">
                    Pipeline {batch!.processed ?? 0}/{batch!.total ?? 0}
                  </p>
                  {batch!.current_lead && (
                    <p className="text-[10px] text-violet-300/70 truncate">
                      {batch!.current_step && STEP_CONFIG[batch!.current_step]
                        ? STEP_CONFIG[batch!.current_step].label
                        : batch!.current_step} — {batch!.current_lead}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}
          {(activeTasks.length > 0 || recentDone.length > 0) && (
            <div className="space-y-0.5 pl-1">
              {[...activeTasks, ...recentDone].map((task) => (
                <TaskRow key={task.task_id} task={task} llm={llm} />
              ))}
            </div>
          )}
          <Link
            href="/activity"
            className="mt-1.5 flex items-center gap-1 pl-1 text-[10px] font-medium text-muted-foreground/60 hover:text-violet-400 transition-colors"
          >
            Ver todo <ChevronRight className="h-2.5 w-2.5" />
          </Link>
        </>
      ) : (
        <div className="pl-1">
          {batchRunning && (
            <div className="flex items-center gap-2 py-1.5">
              <Loader2 className="h-3.5 w-3.5 animate-spin text-violet-500 shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium text-violet-400 truncate">
                  Pipeline {batch!.processed ?? 0}/{batch!.total ?? 0}
                  {batch!.current_step && STEP_CONFIG[batch!.current_step]
                    ? ` · ${STEP_CONFIG[batch!.current_step].label}`
                    : ""}
                </p>
                {batch!.current_lead && (
                  <p className="text-[10px] text-violet-300/70 truncate">
                    {batch!.current_lead}
                  </p>
                )}
              </div>
            </div>
          )}
          {!batchRunning && latestTask && (
            <TaskRow task={latestTask} llm={llm} />
          )}
        </div>
      )}
    </div>
  );
}

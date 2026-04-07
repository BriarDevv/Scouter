"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { getTasks, getLLMSettings, getBatchPipelineStatus } from "@/lib/api/client";
import { useVisibleInterval } from "@/lib/hooks/use-visible-interval";
import type { BatchPipelineProgress } from "@/lib/api/client";
import type { TaskStatusRecord, LLMSettings } from "@/types";
import { STEP_CONFIG, getStepConfig, getModelForStep, isActive } from "@/lib/task-utils";
import { ModelBadge } from "@/components/shared/model-badge";
import {
  BrainCircuit,
  XCircle,
  Loader2,
  Clock,
  CheckCircle2,
  ChevronRight,
} from "lucide-react";

const POLL_INTERVAL = 4_000;

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

const PULSE_STORAGE_KEY = "scouter-activity-expanded";

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
    } catch (err) {
      console.error("activity_pulse_poll_failed", err);
    }
  }, []);

  useEffect(() => {
    getLLMSettings().then(setLlm).catch(() => {});
  }, []);

  useVisibleInterval(poll, POLL_INTERVAL);

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
            IA {batch && batch.status === "running"
              ? `· Pipeline ${batch.processed ?? 0}/${batch.total ?? 0}`
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
          {batch && batch.status === "running" && (
            <div className="mb-1.5 rounded-lg bg-violet-500/10 border border-violet-500/20 px-2.5 py-2 ml-1">
              <div className="flex items-center gap-2">
                <Loader2 className="h-3.5 w-3.5 animate-spin text-violet-500" />
                <div className="min-w-0 flex-1">
                  <p className="text-[11px] font-semibold text-violet-400">
                    Pipeline {batch.processed ?? 0}/{batch.total ?? 0}
                  </p>
                  {batch.current_lead && (
                    <p className="text-[10px] text-violet-300/70 truncate">
                      {batch.current_step && STEP_CONFIG[batch.current_step]
                        ? STEP_CONFIG[batch.current_step].label
                        : batch.current_step} — {batch.current_lead}
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
          {batch && batch.status === "running" && (
            <div className="flex items-center gap-2 py-1.5">
              <Loader2 className="h-3.5 w-3.5 animate-spin text-violet-500 shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium text-violet-400 truncate">
                  Pipeline {batch.processed ?? 0}/{batch.total ?? 0}
                  {batch.current_step && STEP_CONFIG[batch.current_step]
                    ? ` · ${STEP_CONFIG[batch.current_step].label}`
                    : ""}
                </p>
                {batch.current_lead && (
                  <p className="text-[10px] text-violet-300/70 truncate">
                    {batch.current_lead}
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

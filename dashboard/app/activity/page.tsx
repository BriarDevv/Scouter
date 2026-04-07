"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/layout/page-header";
import { SectionHeader } from "@/components/shared/section-header";
import { EmptyState } from "@/components/shared/empty-state";
import { Skeleton, SkeletonCard } from "@/components/shared/skeleton";
import { RelativeTime } from "@/components/shared/relative-time";
import { Button } from "@/components/ui/button";
import { getLeadNames, getLLMSettings } from "@/lib/api/client";
import { useApi } from "@/lib/hooks/use-swr-fetch";
import type { TaskStatusRecord, LLMSettings } from "@/types";
import { getStepConfig, getModelForStep, isActive } from "@/lib/task-utils";
import { ModelBadge } from "@/components/shared/model-badge";
import {
  BrainCircuit,
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
  RefreshCw,
  ArrowRight,
  AlertTriangle,
} from "lucide-react";

const POLL_INTERVAL = 3_000;

function isFailed(status: string) {
  return status === "failed";
}

function isDone(status: string) {
  return ["succeeded", "success"].includes(status);
}

function formatElapsed(start: string | null | undefined): string {
  if (!start) return "";
  const ms = Date.now() - new Date(start).getTime();
  const secs = Math.floor(ms / 1000);
  if (secs < 60) return `${secs}s`;
  const mins = Math.floor(secs / 60);
  const remainSecs = secs % 60;
  return `${mins}m ${remainSecs}s`;
}

function ActiveTaskCard({
  task,
  leadName,
  llm,
}: {
  task: TaskStatusRecord;
  leadName?: string;
  llm: LLMSettings | null;
}) {
  const step = getStepConfig(task.current_step);
  const model = getModelForStep(task.current_step, llm);
  const [elapsed, setElapsed] = useState(() => formatElapsed(task.started_at ?? task.created_at));

  useEffect(() => {
    const id = setInterval(() => {
      setElapsed(formatElapsed(task.started_at ?? task.created_at));
    }, 1000);
    return () => clearInterval(id);
  }, [task.started_at, task.created_at]);

  return (
    <div className="relative overflow-hidden rounded-2xl border border-violet-500/30 bg-card p-5 shadow-sm">
      <div className="absolute inset-0 bg-gradient-to-br from-violet-500/5 to-transparent" />
      <div className="relative">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-50 dark:bg-violet-950/40">
              <Loader2 className="h-5 w-5 animate-spin text-violet-600 dark:text-violet-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <p className="text-sm font-semibold text-foreground font-heading">{step.label}</p>
                <ModelBadge model={model} size="md" />
              </div>
              <p className="text-xs text-muted-foreground">{step.description}</p>
            </div>
          </div>
          <div className="flex items-center gap-1.5 rounded-full bg-violet-50 dark:bg-violet-950/40 px-2.5 py-1">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-violet-500 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-violet-500" />
            </span>
            <span className="text-xs font-medium text-violet-700 dark:text-violet-300 font-data">{elapsed}</span>
          </div>
        </div>

        {task.lead_id && (
          <div className="mt-3 flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Lead:</span>
            <Link
              href={`/leads/${task.lead_id}`}
              className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-0.5 text-xs font-medium text-foreground hover:bg-muted/80 transition-colors"
            >
              {leadName || task.lead_id.slice(0, 12) + "..."}
              <ArrowRight className="h-3 w-3 text-muted-foreground" />
            </Link>
          </div>
        )}

        {task.status === "retrying" && (
          <div className="mt-3 flex items-center gap-2 rounded-lg bg-amber-50 dark:bg-amber-950/20 px-3 py-1.5">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" />
            <span className="text-xs text-amber-700 dark:text-amber-300">Reintentando...</span>
          </div>
        )}
      </div>
    </div>
  );
}

function TaskHistoryRow({
  task,
  leadName,
  llm,
}: {
  task: TaskStatusRecord;
  leadName?: string;
  llm: LLMSettings | null;
}) {
  const step = getStepConfig(task.current_step);
  const StepIcon = step.icon;
  const model = getModelForStep(task.current_step, llm);
  const active = isActive(task.status);
  const failed = isFailed(task.status);
  const done = isDone(task.status);

  return (
    <div className={cn(
      "flex items-center gap-4 rounded-xl px-4 py-3 transition-colors",
      failed && "bg-red-50/50 dark:bg-red-950/10",
    )}>
      {/* Status icon */}
      <div className="shrink-0">
        {active ? (
          <Loader2 className="h-4 w-4 animate-spin text-violet-500" />
        ) : failed ? (
          <XCircle className="h-4 w-4 text-red-500" />
        ) : done ? (
          <CheckCircle2 className="h-4 w-4 text-emerald-500" />
        ) : (
          <Clock className="h-4 w-4 text-muted-foreground" />
        )}
      </div>

      {/* Step */}
      <div className="flex items-center gap-2 min-w-[200px]">
        <StepIcon className="h-3.5 w-3.5 text-muted-foreground" />
        <span className={cn(
          "text-sm font-medium",
          active ? "text-foreground" : "text-muted-foreground"
        )}>
          {step.label}
        </span>
        <ModelBadge model={model} />
      </div>

      {/* Lead */}
      <div className="flex-1 min-w-0">
        {task.lead_id ? (
          <Link
            href={`/leads/${task.lead_id}`}
            className="text-sm text-violet-600 dark:text-violet-400 hover:underline truncate block"
          >
            {leadName || task.lead_id.slice(0, 16) + "..."}
          </Link>
        ) : (
          <span className="text-sm text-muted-foreground">—</span>
        )}
      </div>

      {/* Status badge */}
      <div className="shrink-0">
        <span className={cn(
          "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium",
          active && "bg-violet-50 dark:bg-violet-950/40 text-violet-700 dark:text-violet-300",
          done && "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300",
          failed && "bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300",
          !active && !done && !failed && "bg-muted text-muted-foreground",
        )}>
          {active ? "En curso" : done ? "OK" : failed ? "Error" : task.status}
        </span>
      </div>

      {/* Time */}
      <div className="shrink-0 w-[80px] text-right">
        {task.created_at ? (
          <RelativeTime date={task.created_at} className="text-xs text-muted-foreground" />
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        )}
      </div>

      {/* Error indicator */}
      {task.error && (
        <div className="shrink-0" title={task.error}>
          <AlertTriangle className="h-3.5 w-3.5 text-red-500" />
        </div>
      )}
    </div>
  );
}

export default function ActivityPage() {
  const { data: tasks, isLoading: tasksLoading, mutate: refreshTasks } = useApi<TaskStatusRecord[]>(
    "/tasks?limit=50",
    { refreshInterval: POLL_INTERVAL },
  );
  const [leadMap, setLeadMap] = useState<Record<string, string>>({});
  const [llm, setLlm] = useState<LLMSettings | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getLeadNames(), getLLMSettings()])
      .then(([leadNames, llmData]) => {
        setLlm(llmData);
        const map: Record<string, string> = {};
        for (const lead of leadNames) {
          map[lead.id] = lead.business_name;
        }
        setLeadMap(map);
      })
      .catch((err) => console.warn("Failed to load activity data:", err))
      .finally(() => setLoading(false));
  }, []);

  const taskList = tasks ?? [];
  const activeTasks = taskList.filter((t) => isActive(t.status));
  const failedTasks = taskList.filter((t) => isFailed(t.status));
  const doneTasks = taskList.filter((t) => isDone(t.status));
  const historyTasks = taskList.filter((t) => !isActive(t.status));

  if (loading || tasksLoading) {
    return (
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[1400px] px-8 py-8">
          <div className="space-y-8">
            <PageHeader title="Actividad IA" description="Monitor en tiempo real de tareas y pipelines" />
            <div className="grid gap-4 md:grid-cols-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-24 rounded-2xl" />
              ))}
            </div>
            <SkeletonCard className="h-[400px]" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8">
        <div className="space-y-8">
          <PageHeader title="Actividad IA" description="Monitor en tiempo real de tareas y pipelines">
        <Button variant="outline" size="sm" onClick={() => refreshTasks()} className="gap-2">
          <RefreshCw className="h-3.5 w-3.5" />
          Actualizar
        </Button>
      </PageHeader>

      {/* Summary stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">En curso</p>
              <p className="mt-1 font-data text-3xl font-bold text-foreground">{activeTasks.length}</p>
            </div>
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-violet-50 dark:bg-violet-950/40">
              {activeTasks.length > 0 ? (
                <Loader2 className="h-6 w-6 animate-spin text-violet-600 dark:text-violet-400" />
              ) : (
                <BrainCircuit className="h-6 w-6 text-violet-600 dark:text-violet-400" />
              )}
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Completadas</p>
              <p className="mt-1 font-data text-3xl font-bold text-foreground">{doneTasks.length}</p>
            </div>
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-50 dark:bg-emerald-950/40">
              <CheckCircle2 className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Fallidas</p>
              <p className="mt-1 font-data text-3xl font-bold text-foreground">{failedTasks.length}</p>
            </div>
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-red-50 dark:bg-red-950/40">
              <XCircle className="h-6 w-6 text-red-600 dark:text-red-400" />
            </div>
          </div>
        </div>
      </div>

      {/* Active tasks — hero section */}
      {activeTasks.length > 0 && (
        <div className="space-y-4">
          <SectionHeader
            title="Tareas activas"
            subtitle={`${activeTasks.length} tarea${activeTasks.length > 1 ? "s" : ""} ejecutándose ahora`}
          />
          <div className="grid gap-4 md:grid-cols-2">
            {activeTasks.map((task) => (
              <ActiveTaskCard
                key={task.task_id}
                task={task}
                leadName={task.lead_id ? leadMap[task.lead_id] : undefined}
                llm={llm}
              />
            ))}
          </div>
        </div>
      )}

      {activeTasks.length === 0 && (
        <div className="rounded-2xl border border-dashed border-border bg-card/50 p-8 text-center">
          <BrainCircuit className="mx-auto h-8 w-8 text-muted-foreground/40" />
          <p className="mt-3 text-sm font-medium text-muted-foreground">
            No hay tareas en ejecución
          </p>
          <p className="mt-1 text-xs text-muted-foreground/60">
            Ejecutá un pipeline desde un lead para ver la actividad acá en tiempo real
          </p>
        </div>
      )}

      {/* Failed tasks — if any */}
      {failedTasks.length > 0 && (
        <div className="space-y-3">
          <SectionHeader
            title="Errores recientes"
            subtitle="Tareas que fallaron y pueden requerir atención"
          />
          <div className="rounded-2xl border border-red-200 dark:border-red-900/30 bg-card overflow-hidden">
            <div className="divide-y divide-border">
              {failedTasks.map((task) => (
                <div key={task.task_id} className="px-5 py-4">
                  <div className="flex items-start gap-3">
                    <XCircle className="h-4 w-4 mt-0.5 shrink-0 text-red-500" />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-foreground">
                          {getStepConfig(task.current_step).label}
                        </span>
                        {task.created_at && (
                          <RelativeTime date={task.created_at} className="text-xs text-muted-foreground" />
                        )}
                      </div>
                      {task.lead_id && (
                        <Link
                          href={`/leads/${task.lead_id}`}
                          className="text-xs text-violet-600 dark:text-violet-400 hover:underline"
                        >
                          {leadMap[task.lead_id] || task.lead_id.slice(0, 16) + "..."}
                        </Link>
                      )}
                      {task.error && (
                        <p className="mt-1 text-xs text-red-600 dark:text-red-400 font-data break-all">
                          {task.error}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* History */}
      {historyTasks.length > 0 && (
        <div className="space-y-3">
          <SectionHeader
            title="Historial"
            subtitle={`Últimas ${historyTasks.length} tareas completadas`}
          />
          <div className="rounded-2xl border border-border bg-card overflow-hidden">
            {/* Header */}
            <div className="flex items-center gap-4 border-b border-border px-4 py-2.5 bg-muted/30">
              <div className="shrink-0 w-4" />
              <div className="min-w-[200px] text-xs font-medium text-muted-foreground uppercase tracking-wider">Paso</div>
              <div className="flex-1 text-xs font-medium text-muted-foreground uppercase tracking-wider">Lead</div>
              <div className="shrink-0 text-xs font-medium text-muted-foreground uppercase tracking-wider">Estado</div>
              <div className="shrink-0 w-[80px] text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">Cuándo</div>
              <div className="shrink-0 w-3.5" />
            </div>
            <div className="divide-y divide-border/50">
              {historyTasks.map((task, i) => (
                <div key={task.task_id} className={cn(i % 2 === 1 && "bg-muted/10")}>
                  <TaskHistoryRow
                    task={task}
                    leadName={task.lead_id ? leadMap[task.lead_id] : undefined}
                    llm={llm}
                  />
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {taskList.length === 0 && (
        <EmptyState
          icon={BrainCircuit}
          title="Sin actividad"
          description="Todavía no se ejecutó ninguna tarea. Ejecutá un pipeline desde la vista de un lead para ver la actividad acá."
        />
      )}
        </div>
      </div>
    </div>
  );
}

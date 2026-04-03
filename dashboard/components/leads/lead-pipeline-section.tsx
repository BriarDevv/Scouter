"use client";

import { CollapsibleSection } from "@/components/shared/collapsible-section";
import { RelativeTime } from "@/components/shared/relative-time";
import { GitBranch } from "lucide-react";
import type { PipelineRunSummary, TaskStatusRecord } from "@/types";

interface LeadPipelineSectionProps {
  pipelineRuns: PipelineRunSummary[];
  latestTask: TaskStatusRecord | null;
}

export function LeadPipelineSection({ pipelineRuns, latestTask }: LeadPipelineSectionProps) {
  return (
    <CollapsibleSection
      title="Pipeline Async"
      icon={GitBranch}
      defaultOpen={false}
      badge={
        latestTask?.task_id ? (
          <span className="text-xs text-muted-foreground font-data">task {latestTask.task_id.slice(0, 8)}</span>
        ) : undefined
      }
    >
      {latestTask && (
        <div className="mb-4 rounded-xl border border-violet-100 dark:border-violet-900/30 bg-violet-50/40 dark:bg-violet-950/20 p-3">
          <p className="text-xs font-medium text-violet-700 dark:text-violet-300">Última task</p>
          <p className="mt-1 text-sm text-foreground/80">
            {latestTask.status} {latestTask.current_step ? `· ${latestTask.current_step}` : ""}
          </p>
          {latestTask.pipeline_run_id && (
            <p className="mt-1 text-xs text-muted-foreground font-data">run {latestTask.pipeline_run_id.slice(0, 8)}</p>
          )}
        </div>
      )}
      {pipelineRuns.length > 0 ? (
        <div className="space-y-3">
          {pipelineRuns.map((run) => (
            <div key={run.id} className="rounded-xl border border-border p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-foreground">
                    {run.status} {run.current_step ? `· ${run.current_step}` : ""}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground font-data">
                    run {run.id.slice(0, 8)} · <RelativeTime date={run.updated_at} />
                  </p>
                </div>
                {run.root_task_id && (
                  <span className="text-xs text-muted-foreground font-data">{run.root_task_id.slice(0, 8)}</span>
                )}
              </div>
              {run.error && <p className="mt-2 text-xs text-red-600">{run.error}</p>}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground text-center py-6">Sin ejecuciones async registradas</p>
      )}
    </CollapsibleSection>
  );
}

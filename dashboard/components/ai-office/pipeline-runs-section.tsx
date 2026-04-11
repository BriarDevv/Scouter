"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api/client";
import { PipelineProgress } from "@/components/ai-office/pipeline-progress";
import {
  Activity, RefreshCw, Loader2, CheckCircle, XCircle, Clock,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface PipelineRunItem {
  id: string;
  lead_id: string;
  status: string;
  current_step: string | null;
  correlation_id: string;
  created_at: string;
  finished_at: string | null;
  error: string | null;
  step_context_json?: Record<string, unknown>;
}

const STATUS_ICON: Record<string, typeof CheckCircle> = {
  succeeded: CheckCircle,
  failed: XCircle,
  running: Loader2,
};

const STATUS_STYLE: Record<string, string> = {
  succeeded: "text-green-500",
  failed: "text-red-500",
  running: "text-blue-500 animate-spin",
};

export function PipelineRunsSection() {
  const [runs, setRuns] = useState<PipelineRunItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [resuming, setResuming] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("all");

  const loadRuns = async () => {
    try {
      const data = await apiFetch<PipelineRunItem[]>("/pipelines/runs?page_size=30");
      setRuns(Array.isArray(data) ? data : []);
    } catch (err) { console.error("pipeline_runs_fetch_failed", err); }
    setLoading(false);
  };

  // Canonical data-fetch-on-mount — setRuns/setLoading is the effect's purpose.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadRuns();
  }, []);

  const handleResume = async (runId: string) => {
    setResuming(runId);
    try {
      await apiFetch(`/pipelines/runs/${runId}/resume`, { method: "POST" });
      await loadRuns();
    } catch (err) { console.error("pipeline_run_resume_failed", err); }
    setResuming(null);
  };

  const filtered = filter === "all"
    ? runs
    : runs.filter((r) => r.status === filter);

  const counts = {
    all: runs.length,
    succeeded: runs.filter((r) => r.status === "succeeded").length,
    failed: runs.filter((r) => r.status === "failed").length,
    running: runs.filter((r) => r.status === "running").length,
  };

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-cyan-600 dark:text-cyan-400" />
          <h3 className="text-sm font-medium">Pipeline Runs</h3>
        </div>
        <button onClick={loadRuns} className="text-xs text-muted-foreground hover:text-foreground">
          <RefreshCw className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 mb-3">
        {(["all", "running", "failed", "succeeded"] as const).map((key) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={cn(
              "text-xs px-2 py-1 rounded-md transition-colors",
              filter === key
                ? "bg-foreground/10 text-foreground font-medium"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            {key === "all" ? "Todos" : key} ({counts[key]})
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex justify-center py-4"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div>
      ) : filtered.length === 0 ? (
        <p className="text-sm text-muted-foreground">Sin pipeline runs{filter !== "all" ? ` con status "${filter}"` : ""}.</p>
      ) : (
        <div className="space-y-2 max-h-[400px] overflow-y-auto">
          {filtered.map((run) => {
            const Icon = STATUS_ICON[run.status] || Clock;
            const isStuck = run.status === "running" && !run.finished_at;
            const contextKeys = run.step_context_json ? Object.keys(run.step_context_json) : [];

            return (
              <div key={run.id} className="rounded-lg border border-border/50 p-2.5">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <Icon className={cn("h-3.5 w-3.5 shrink-0", STATUS_STYLE[run.status] || "text-muted-foreground")} />
                    <span className="text-xs font-mono text-muted-foreground truncate">{run.lead_id.slice(0, 8)}...</span>
                    <span className="text-xs text-muted-foreground">step: {run.current_step || "?"}</span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-xs text-muted-foreground">
                      {run.created_at ? new Date(run.created_at).toLocaleDateString("es-AR") : ""}
                    </span>
                    {isStuck && (
                      <button
                        onClick={() => handleResume(run.id)}
                        disabled={resuming === run.id}
                        className="text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-700 hover:bg-blue-200 dark:bg-blue-900/30 dark:text-blue-300 disabled:opacity-50"
                      >
                        {resuming === run.id ? "..." : "Resume"}
                      </button>
                    )}
                  </div>
                </div>
                {run.error && (
                  <p className="text-xs text-red-500 mt-1 truncate">{run.error}</p>
                )}
                {contextKeys.length > 0 && (
                  <div className="mt-1.5">
                    <PipelineProgress
                      currentStep={run.current_step}
                      status={run.status}
                      contextKeys={contextKeys}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

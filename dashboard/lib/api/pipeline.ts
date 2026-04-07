import type {
  PipelineRunSummary,
  StepContext,
} from "@/types";
import type { BatchPipelineProgress } from "@/types/pipeline";
import { apiFetch } from "./client";

// ─── Pipeline Runs ─────────────────────────────────────

export async function getPipelineRuns(params?: {
  lead_id?: string;
  status?: string;
  limit?: number;
}): Promise<PipelineRunSummary[]> {
  const query = new URLSearchParams();
  if (params?.lead_id) query.set("lead_id", params.lead_id);
  if (params?.status) query.set("status", params.status);
  if (params?.limit) query.set("limit", String(params.limit));
  const suffix = query.size ? `?${query.toString()}` : "";
  return apiFetch(`/pipelines/runs${suffix}`);
}

// ─── Batch Pipeline ───────────────────────────────────

export async function getBatchPipelineStatus(): Promise<BatchPipelineProgress | null> {
  try {
    return await apiFetch<BatchPipelineProgress>("/pipelines/batch/status");
  } catch (err) {
    console.error("batch_pipeline_status_fetch_failed", err);
    return null;
  }
}

// ─── Agent OS: Pipeline Context ─────────────────────────────────────

export async function getPipelineContext(pipelineRunId: string): Promise<StepContext> {
  return apiFetch<StepContext>(`/pipelines/runs/${pipelineRunId}/context`);
}

// Re-export types for backward compatibility
export type { BatchPipelineProgress } from "@/types/pipeline";

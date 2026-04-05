"use client";

import { cn } from "@/lib/utils";
import { CheckCircle, Circle, XCircle, Loader2 } from "lucide-react";

const PIPELINE_STEPS = [
  { key: "pipeline_dispatch", label: "Dispatch" },
  { key: "enrichment", label: "Enrichment" },
  { key: "scoring", label: "Scoring" },
  { key: "analysis", label: "Analysis" },
  { key: "research", label: "Scout Research" },
  { key: "brief_generation", label: "Brief" },
  { key: "brief_review", label: "Brief Review" },
  { key: "draft_generation", label: "Draft" },
];

interface PipelineProgressProps {
  currentStep: string | null;
  status: string;
  contextKeys?: string[];
}

function getStepState(
  stepKey: string,
  currentStep: string | null,
  pipelineStatus: string,
  contextKeys: string[]
): "completed" | "active" | "failed" | "pending" {
  const stepIndex = PIPELINE_STEPS.findIndex((s) => s.key === stepKey);
  const currentIndex = PIPELINE_STEPS.findIndex((s) => s.key === currentStep);

  // Map context keys to step keys for completion detection
  const contextToStep: Record<string, string> = {
    enrichment: "enrichment",
    scoring: "scoring",
    analysis: "analysis",
    scout: "research",
    research: "research",
    brief: "brief_generation",
    brief_review: "brief_review",
  };

  const completedSteps = new Set(
    contextKeys
      .map((k) => contextToStep[k])
      .filter(Boolean)
  );

  if (completedSteps.has(stepKey)) return "completed";
  if (stepKey === "pipeline_dispatch" && currentIndex >= 0) return "completed";
  if (stepKey === currentStep) {
    return pipelineStatus === "failed" ? "failed" : "active";
  }
  if (stepIndex < currentIndex) return "completed";
  return "pending";
}

const STATE_STYLES = {
  completed: { icon: CheckCircle, color: "text-green-500", bg: "bg-green-500/10", border: "border-green-500/30" },
  active: { icon: Loader2, color: "text-blue-500", bg: "bg-blue-500/10", border: "border-blue-500/30" },
  failed: { icon: XCircle, color: "text-red-500", bg: "bg-red-500/10", border: "border-red-500/30" },
  pending: { icon: Circle, color: "text-muted-foreground/40", bg: "bg-muted/30", border: "border-border/30" },
};

export function PipelineProgress({ currentStep, status, contextKeys = [] }: PipelineProgressProps) {
  return (
    <div className="flex items-center gap-1 overflow-x-auto py-1">
      {PIPELINE_STEPS.map((step, i) => {
        const state = getStepState(step.key, currentStep, status, contextKeys);
        const styles = STATE_STYLES[state];
        const Icon = styles.icon;

        return (
          <div key={step.key} className="flex items-center">
            <div
              className={cn(
                "flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs",
                styles.bg,
                styles.border,
                styles.color,
              )}
            >
              <Icon className={cn("h-3 w-3", state === "active" && "animate-spin")} />
              <span className="whitespace-nowrap">{step.label}</span>
            </div>
            {i < PIPELINE_STEPS.length - 1 && (
              <div className="w-2 h-px bg-border mx-0.5" />
            )}
          </div>
        );
      })}
    </div>
  );
}

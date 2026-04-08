"use client";

import { useEffect, useState } from "react";
import { CollapsibleSection } from "@/components/shared/collapsible-section";
import { Brain, Search, FileText, CheckCircle, AlertTriangle, Sparkles } from "lucide-react";
import { getPipelineContext, getInvestigation } from "@/lib/api/client";
import type { StepContext, InvestigationThread } from "@/types";
import { InvestigationThreadView } from "./investigation-thread";

interface AiDecisionsPanelProps {
  leadId: string;
  pipelineRunId?: string | null;
}

const QUALITY_COLORS: Record<string, string> = {
  high: "text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/30",
  medium: "text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/30",
  low: "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/30",
};

export function AiDecisionsPanel({ leadId, pipelineRunId }: AiDecisionsPanelProps) {
  const [context, setContext] = useState<StepContext | null>(null);
  const [investigation, setInvestigation] = useState<InvestigationThread | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [ctx, inv] = await Promise.all([
          pipelineRunId ? getPipelineContext(pipelineRunId).catch(() => null) : null,
          getInvestigation(leadId).catch(() => null),
        ]);
        setContext(ctx);
        setInvestigation(inv);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [leadId, pipelineRunId]);

  if (loading) {
    return (
      <CollapsibleSection title="Decisiones IA" icon={Brain} defaultOpen={false}>
        <p className="text-sm text-muted-foreground">Cargando...</p>
      </CollapsibleSection>
    );
  }

  if (!context && !investigation) {
    return (
      <CollapsibleSection title="Decisiones IA" icon={Brain} defaultOpen={false}>
        <p className="text-sm text-muted-foreground">Sin datos de pipeline para este lead.</p>
      </CollapsibleSection>
    );
  }

  return (
    <CollapsibleSection
      title="Decisiones IA"
      icon={Brain}
      defaultOpen={false}
      badge={
        context?.analysis?.quality ? (
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${QUALITY_COLORS[context.analysis.quality] || ""}`}>
            {context.analysis.quality.toUpperCase()}
          </span>
        ) : undefined
      }
    >
      <div className="space-y-4">
        {/* Analysis */}
        {context?.analysis && (
          <StepCard
            icon={Sparkles}
            title="Analisis (Executor 9b)"
            color="violet"
          >
            <p className="text-sm text-foreground/80">{context.analysis.reasoning}</p>
            {context.analysis.suggested_angle && (
              <p className="mt-1 text-xs text-muted-foreground">
                Angulo sugerido: {context.analysis.suggested_angle}
              </p>
            )}
          </StepCard>
        )}

        {/* Scout Investigation */}
        {investigation && (
          <InvestigationThreadView investigation={investigation} />
        )}

        {/* Brief */}
        {context?.brief && (
          <StepCard icon={FileText} title="Brief Comercial (Executor 9b)" color="blue">
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-muted-foreground">Oportunidad:</span>{" "}
                <span className="font-medium">{context.brief.opportunity_score ?? "?"}/100</span>
              </div>
              <div>
                <span className="text-muted-foreground">Budget:</span>{" "}
                <span className="font-medium">{context.brief.budget_tier ?? "?"}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Canal:</span>{" "}
                <span className="font-medium">{context.brief.recommended_contact_method ?? "?"}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Scope:</span>{" "}
                <span className="font-medium">{context.brief.estimated_scope ?? "?"}</span>
              </div>
            </div>
            {context.brief.recommended_angle && (
              <p className="mt-2 text-xs text-muted-foreground">
                Angulo: {context.brief.recommended_angle}
              </p>
            )}
          </StepCard>
        )}

        {/* Brief Review */}
        {context?.brief_review && (
          <StepCard
            icon={context.brief_review.approved ? CheckCircle : AlertTriangle}
            title="Review (Reviewer 27b)"
            color={context.brief_review.approved ? "emerald" : "amber"}
          >
            <p className="text-sm text-foreground/80">
              {context.brief_review.approved ? "Aprobado" : "Necesita revision"}
            </p>
            {context.brief_review.verdict_reasoning && (
              <p className="mt-1 text-xs text-muted-foreground">{context.brief_review.verdict_reasoning}</p>
            )}
          </StepCard>
        )}

        {/* Enrichment + Scoring summary */}
        {(context?.enrichment || context?.scoring) && (
          <div className="rounded-lg border border-border/50 bg-muted/20 p-3">
            <p className="text-xs font-medium text-muted-foreground mb-1">Enrichment + Scoring</p>
            <div className="flex flex-wrap gap-2">
              {context?.scoring?.score != null && (
                <span className="text-xs bg-background border border-border rounded px-2 py-0.5">
                  Score: {context.scoring.score}
                </span>
              )}
              {context?.enrichment?.signals?.map((s) => (
                <span key={s} className="text-xs bg-background border border-border rounded px-2 py-0.5">
                  {s}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </CollapsibleSection>
  );
}

const STEP_COLOR_CLASSES: Record<string, { border: string; bg: string; title: string }> = {
  violet:  { border: "border-border",                                  bg: "bg-muted/50 dark:bg-muted/50",            title: "text-foreground dark:text-foreground" },
  blue:    { border: "border-blue-100 dark:border-blue-900/30",       bg: "bg-blue-50/40 dark:bg-blue-950/20",       title: "text-blue-700 dark:text-blue-300" },
  emerald: { border: "border-emerald-100 dark:border-emerald-900/30", bg: "bg-emerald-50/40 dark:bg-emerald-950/20", title: "text-emerald-700 dark:text-emerald-300" },
  amber:   { border: "border-amber-100 dark:border-amber-900/30",     bg: "bg-amber-50/40 dark:bg-amber-950/20",     title: "text-amber-700 dark:text-amber-300" },
};

function StepCard({
  icon: Icon,
  title,
  color,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  color: string;
  children: React.ReactNode;
}) {
  const classes = STEP_COLOR_CLASSES[color] ?? STEP_COLOR_CLASSES.violet;

  return (
    <div className={`rounded-xl border ${classes.border} ${classes.bg} p-3`}>
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`h-4 w-4 ${classes.title}`} />
        <p className={`text-xs font-medium ${classes.title}`}>{title}</p>
      </div>
      {children}
    </div>
  );
}

"use client";

import { Button } from "@/components/ui/button";
import { CollapsibleSection } from "@/components/shared/collapsible-section";
import { EmptyState } from "@/components/shared/empty-state";
import { Sparkles, RefreshCw, Loader2 } from "lucide-react";
import type { Lead } from "@/types";

interface LeadAnalysisSectionProps {
  lead: Lead;
  isRunningPipeline: boolean;
  onRunPipeline: () => void;
}

export function LeadAnalysisSection({ lead, isRunningPipeline, onRunPipeline }: LeadAnalysisSectionProps) {
  return (
    <CollapsibleSection
      title="Análisis IA"
      icon={Sparkles}
      defaultOpen
    >
      {lead.llm_summary ? (
        <div className="space-y-3">
          <p className="text-sm text-foreground/80 leading-relaxed">{lead.llm_summary}</p>
          {lead.llm_quality_assessment && (
            <div className="rounded-xl bg-muted/60 p-3">
              <p className="text-xs font-medium text-muted-foreground mb-1">Evaluación de calidad</p>
              <p className="text-sm text-foreground/80">{lead.llm_quality_assessment}</p>
            </div>
          )}
          {lead.llm_suggested_angle && (
            <div className="rounded-xl bg-muted/60 p-3">
              <p className="text-xs font-medium text-muted-foreground mb-1">Ángulo comercial sugerido</p>
              <p className="text-sm text-foreground/80">{lead.llm_suggested_angle}</p>
            </div>
          )}
        </div>
      ) : (
        <EmptyState
          icon={Sparkles}
          title="Análisis IA no disponible"
          description="Ejecutá el pipeline para generar el análisis con el modelo configurado en Ollama."
          className="py-6"
        >
          <Button
            variant="outline"
            size="sm"
            className="rounded-xl gap-1.5"
            onClick={onRunPipeline}
            disabled={isRunningPipeline}
          >
            {isRunningPipeline ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            Ejecutar Análisis
          </Button>
        </EmptyState>
      )}
    </CollapsibleSection>
  );
}

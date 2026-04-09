"use client";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/shared/empty-state";
import type { Lead, CommercialBrief, LeadResearchReport } from "@/types";
import { Sparkles, FileText, Search, Loader2, RefreshCw, Briefcase, Camera } from "lucide-react";
import { cn } from "@/lib/utils";
import { API_BASE_URL } from "@/lib/constants";

interface LeadSummaryTabProps {
  lead: Lead;
  brief: CommercialBrief | null;
  research: LeadResearchReport | null;
  isRunningPipeline: boolean;
  isRunningResearch: boolean;
  isGeneratingBrief: boolean;
  onRunPipeline: () => void;
  onRunResearch: () => void;
  onGenerateBrief: () => void;
}

function BriefStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-muted p-2.5 text-center">
      <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground block">{label}</span>
      <span className="text-xs font-medium text-foreground mt-0.5 block capitalize">{value}</span>
    </div>
  );
}

function ResearchChip({ label, detected }: { label: string; detected: boolean | null }) {
  return (
    <span className={cn(
      "inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-[10px] font-medium",
      detected ? "bg-emerald-50/60 dark:bg-emerald-950/20 text-emerald-700 dark:text-emerald-300"
        : "bg-muted text-muted-foreground"
    )}>
      <span className={cn("h-1.5 w-1.5 rounded-full", detected ? "bg-emerald-500" : "bg-muted-foreground/30")} />
      {label}
    </span>
  );
}

export function LeadSummaryTab({
  lead, brief, research,
  isRunningPipeline, isRunningResearch, isGeneratingBrief,
  onRunPipeline, onRunResearch, onGenerateBrief,
}: LeadSummaryTabProps) {
  const hasAnalysis = lead.llm_summary || lead.llm_quality_assessment || lead.llm_suggested_angle;
  const hasBrief = brief !== null && (brief.status === "generated" || brief.status === "reviewed");
  const hasResearch = research !== null && research.status === "completed";

  return (
    <div className="space-y-4">
      {/* AI Analysis */}
      <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-semibold text-foreground font-heading">Análisis IA</h3>
        </div>
        {hasAnalysis ? (
          <div className="space-y-3">
            {lead.llm_summary && (
              <p className="text-sm text-muted-foreground leading-relaxed">{lead.llm_summary}</p>
            )}
            {(lead.llm_quality_assessment || lead.llm_suggested_angle) && (
              <div className="grid gap-3 sm:grid-cols-2">
                {lead.llm_quality_assessment && (
                  <div className="rounded-xl bg-muted p-3">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Evaluación</span>
                    <p className="mt-1 text-xs text-foreground leading-relaxed">{lead.llm_quality_assessment}</p>
                  </div>
                )}
                {lead.llm_suggested_angle && (
                  <div className="rounded-xl bg-muted p-3">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Ángulo sugerido</span>
                    <p className="mt-1 text-xs text-foreground leading-relaxed">{lead.llm_suggested_angle}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <EmptyState icon={Sparkles} title="Sin análisis" description="Ejecutá el pipeline para generar el análisis IA." className="py-4">
            <Button variant="outline" size="sm" className="rounded-xl gap-1.5" onClick={onRunPipeline} disabled={isRunningPipeline}>
              {isRunningPipeline ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
              Pipeline
            </Button>
          </EmptyState>
        )}
      </div>

      {/* Brief Commercial */}
      <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <Briefcase className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-semibold text-foreground font-heading">Brief Comercial</h3>
        </div>
        {hasBrief ? (
          <div className="space-y-3">
            <div className="grid gap-2 grid-cols-2 sm:grid-cols-4">
              <BriefStat label="Oportunidad" value={brief.opportunity_score != null ? `${brief.opportunity_score.toFixed(0)}/100` : "—"} />
              <BriefStat label="Budget" value={brief.budget_tier || "—"} />
              <BriefStat label="Scope" value={brief.estimated_scope?.replace(/_/g, " ") || "—"} />
              <BriefStat label="Prioridad" value={brief.contact_priority || "—"} />
            </div>
            {brief.why_this_lead_matters && (
              <div className="rounded-xl bg-muted p-3">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Por qué importa</span>
                <p className="mt-1 text-xs text-foreground leading-relaxed">{brief.why_this_lead_matters}</p>
              </div>
            )}
            {brief.recommended_angle && (
              <div className="rounded-xl bg-muted p-3">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Ángulo recomendado</span>
                <p className="mt-1 text-xs text-foreground leading-relaxed">{brief.recommended_angle}</p>
              </div>
            )}
          </div>
        ) : (
          <EmptyState icon={Briefcase} title="Sin brief" description="Generá el brief comercial para este lead." className="py-4">
            <Button variant="outline" size="sm" className="rounded-xl gap-1.5" onClick={onGenerateBrief} disabled={isGeneratingBrief}>
              {isGeneratingBrief ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Briefcase className="h-3.5 w-3.5" />}
              Generar Brief
            </Button>
          </EmptyState>
        )}
      </div>

      {/* Research Summary */}
      <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <Search className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-semibold text-foreground font-heading">Investigación</h3>
        </div>
        {hasResearch ? (
          <div className="space-y-3">
            {research.business_description && (
              <p className="text-sm text-muted-foreground leading-relaxed">{research.business_description}</p>
            )}
            <div className="flex flex-wrap gap-2">
              <ResearchChip label="Website" detected={research.website_exists} />
              <ResearchChip label="Instagram" detected={research.instagram_exists} />
              <ResearchChip label="WhatsApp" detected={research.whatsapp_detected} />
            </div>
            {research.detected_signals_json && research.detected_signals_json.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {research.detected_signals_json.slice(0, 6).map((sig, i) => (
                  <span key={i} className="rounded-lg bg-muted px-2 py-1 text-[10px] text-muted-foreground">
                    {sig.type}{sig.detail ? `: ${sig.detail}` : ""}
                  </span>
                ))}
              </div>
            )}
          </div>
        ) : (
          <EmptyState icon={Search} title="Sin investigación" description="Ejecutá la investigación del Scout." className="py-4">
            <Button variant="outline" size="sm" className="rounded-xl gap-1.5" onClick={onRunResearch} disabled={isRunningResearch}>
              {isRunningResearch ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Search className="h-3.5 w-3.5" />}
              Investigar
            </Button>
          </EmptyState>
        )}
      </div>

      {/* Screenshots */}
      {(lead.website_url || (research?.screenshots_json && research.screenshots_json.length > 0)) && (
        <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-3">
            <Camera className="h-4 w-4 text-muted-foreground" />
            <h3 className="text-sm font-semibold text-foreground font-heading">Capturas</h3>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {lead.website_url && (
              <a
                href={`${API_BASE_URL}/leads/${lead.id}/screenshot`}
                target="_blank"
                rel="noopener noreferrer"
                className="block rounded-xl border border-border overflow-hidden hover:border-foreground/20 transition-colors"
              >
                <img
                  src={`${API_BASE_URL}/leads/${lead.id}/screenshot`}
                  alt={`Screenshot de ${lead.business_name}`}
                  className="w-full object-cover object-top"
                  loading="lazy"
                  onError={(e) => {
                    (e.target as HTMLElement).closest("a")!.style.display = "none";
                  }}
                />
              </a>
            )}
            {research?.screenshots_json?.map((shot, i) => (
              <a
                key={i}
                href={shot.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block rounded-xl border border-border overflow-hidden hover:border-foreground/20 transition-colors"
              >
                <img
                  src={shot.path.startsWith("http") ? shot.path : `${API_BASE_URL}/${shot.path}`}
                  alt={`Captura ${i + 1}`}
                  className="w-full object-cover object-top"
                  loading="lazy"
                />
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

"use client";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/shared/empty-state";
import { Loader2, Briefcase, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { CommercialBrief } from "@/types";

interface LeadBriefSectionProps {
  brief: CommercialBrief | null;
  isGeneratingBrief: boolean;
  onGenerateBrief: () => void;
}

function BriefStat({ label, value, variant }: { label: string; value: string; variant?: "emerald" | "amber" | "red" | "default" }) {
  return (
    <div className="rounded-xl bg-muted p-2.5 text-center">
      <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground block">{label}</span>
      <span className={cn(
        "text-xs font-medium mt-0.5 block capitalize",
        variant === "emerald" ? "text-emerald-700 dark:text-emerald-300"
          : variant === "amber" ? "text-amber-700 dark:text-amber-300"
          : variant === "red" ? "text-red-700 dark:text-red-300"
          : "text-foreground"
      )}>{value}</span>
    </div>
  );
}

function priorityVariant(p: string | null): "emerald" | "amber" | "red" | "default" {
  if (p === "immediate") return "red";
  if (p === "high") return "amber";
  return "default";
}

function budgetVariant(b: string | null): "emerald" | "amber" | "red" | "default" {
  if (b === "premium") return "emerald";
  if (b === "high") return "amber";
  return "default";
}

export function LeadBriefSection({ brief, isGeneratingBrief, onGenerateBrief }: LeadBriefSectionProps) {
  if (!brief || (brief.status !== "generated" && brief.status !== "reviewed" && brief.status !== "failed")) {
    return (
      <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <Briefcase className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-semibold text-foreground font-heading">Brief Comercial</h3>
        </div>
        <EmptyState icon={Briefcase} title="Sin brief comercial" description="Generá un brief comercial para evaluar la oportunidad." className="py-4">
          <Button variant="outline" size="sm" className="rounded-xl gap-1.5" onClick={onGenerateBrief} disabled={isGeneratingBrief}>
            {isGeneratingBrief ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Briefcase className="h-3.5 w-3.5" />}
            Generar Brief
          </Button>
        </EmptyState>
      </div>
    );
  }

  if (brief.status === "failed") {
    return (
      <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <Briefcase className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-semibold text-foreground font-heading">Brief Comercial</h3>
        </div>
        <div className="flex items-center gap-2 rounded-xl bg-red-50 dark:bg-red-950/20 px-3 py-2.5 text-xs text-red-700 dark:text-red-300">
          <AlertCircle className="h-3.5 w-3.5 shrink-0" />
          {brief.error || "Error al generar brief"}
        </div>
        <Button variant="outline" size="sm" className="rounded-xl gap-1.5 mt-3" onClick={onGenerateBrief} disabled={isGeneratingBrief}>
          {isGeneratingBrief ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Briefcase className="h-3.5 w-3.5" />}
          Reintentar
        </Button>
      </div>
    );
  }

  const scoreVariant = (brief.opportunity_score ?? 0) >= 70 ? "emerald" as const : (brief.opportunity_score ?? 0) >= 40 ? "amber" as const : "red" as const;

  return (
    <div className="space-y-4">
      {/* KPIs */}
      <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Briefcase className="h-4 w-4 text-muted-foreground" />
            <h3 className="text-sm font-semibold text-foreground font-heading">Brief Comercial</h3>
          </div>
          <span className={cn(
            "rounded-full px-2.5 py-0.5 text-[10px] font-medium",
            brief.status === "reviewed" ? "bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300" : "bg-muted text-muted-foreground"
          )}>{brief.status}</span>
        </div>
        <div className="grid gap-2 grid-cols-2 sm:grid-cols-4">
          <BriefStat label="Oportunidad" value={brief.opportunity_score != null ? `${brief.opportunity_score.toFixed(0)}/100` : "—"} variant={scoreVariant} />
          <BriefStat label="Budget" value={brief.budget_tier || "—"} variant={budgetVariant(brief.budget_tier)} />
          <BriefStat label="Scope" value={brief.estimated_scope?.replace(/_/g, " ") || "—"} />
          <BriefStat label="Prioridad" value={brief.contact_priority || "—"} variant={priorityVariant(brief.contact_priority)} />
        </div>
        {brief.estimated_budget_min != null && brief.estimated_budget_max != null && (
          <p className="mt-3 text-xs text-muted-foreground text-center font-data">
            USD {brief.estimated_budget_min.toLocaleString()} – {brief.estimated_budget_max.toLocaleString()}
          </p>
        )}
      </div>

      {/* Contact strategy */}
      {(brief.recommended_contact_method || brief.should_call || brief.demo_recommended) && (
        <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Estrategia de contacto</span>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {brief.recommended_contact_method && (
              <span className="rounded-full bg-muted px-2.5 py-0.5 text-[10px] font-medium text-foreground">
                {brief.recommended_contact_method.replace(/_/g, " ")}
              </span>
            )}
            {brief.should_call && (
              <span className={cn(
                "rounded-full px-2.5 py-0.5 text-[10px] font-medium",
                brief.should_call === "yes" ? "bg-emerald-50 dark:bg-emerald-950/20 text-emerald-700 dark:text-emerald-300"
                  : brief.should_call === "maybe" ? "bg-amber-50 dark:bg-amber-950/20 text-amber-700 dark:text-amber-300"
                  : "bg-muted text-muted-foreground"
              )}>Llamar: {brief.should_call}</span>
            )}
            {brief.demo_recommended && (
              <span className="rounded-full bg-muted px-2.5 py-0.5 text-[10px] font-medium text-foreground">Demo recomendada</span>
            )}
          </div>
          {brief.call_reason && (
            <div className="mt-3 rounded-xl bg-muted p-3">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Razón de llamada</span>
              <p className="mt-1 text-xs text-foreground leading-relaxed">{brief.call_reason}</p>
            </div>
          )}
        </div>
      )}

      {/* Why this lead matters */}
      {brief.why_this_lead_matters && (
        <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Por qué importa</span>
          <p className="mt-2 text-sm text-muted-foreground leading-relaxed">{brief.why_this_lead_matters}</p>
        </div>
      )}

      {/* Signals & gaps */}
      {((brief.main_business_signals && brief.main_business_signals.length > 0) || (brief.main_digital_gaps && brief.main_digital_gaps.length > 0)) && (
        <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
          <div className="grid gap-5 sm:grid-cols-2">
            {brief.main_business_signals && brief.main_business_signals.length > 0 && (
              <div>
                <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Señales de negocio</span>
                <div className="mt-2 space-y-1">
                  {brief.main_business_signals.map((sig, i) => (
                    <div key={i} className="rounded-xl bg-muted px-3 py-2 text-xs text-foreground">{sig}</div>
                  ))}
                </div>
              </div>
            )}
            {brief.main_digital_gaps && brief.main_digital_gaps.length > 0 && (
              <div>
                <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Brechas digitales</span>
                <div className="mt-2 space-y-1">
                  {brief.main_digital_gaps.map((gap, i) => (
                    <div key={i} className="rounded-xl bg-muted px-3 py-2 text-xs text-foreground">{gap}</div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Recommended angle */}
      {brief.recommended_angle && (
        <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Ángulo recomendado</span>
          <p className="mt-2 text-sm text-muted-foreground leading-relaxed">{brief.recommended_angle}</p>
        </div>
      )}
    </div>
  );
}

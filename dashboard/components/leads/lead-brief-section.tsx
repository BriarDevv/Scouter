"use client";

import { Button } from "@/components/ui/button";
import { CollapsibleSection } from "@/components/shared/collapsible-section";
import { EmptyState } from "@/components/shared/empty-state";
import { Loader2, Briefcase, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { CommercialBrief } from "@/types";

interface LeadBriefSectionProps {
  brief: CommercialBrief | null;
  isGeneratingBrief: boolean;
  onGenerateBrief: () => void;
}

export function LeadBriefSection({ brief, isGeneratingBrief, onGenerateBrief }: LeadBriefSectionProps) {
  return (
    <CollapsibleSection
      title="Brief Comercial"
      icon={Briefcase}
      defaultOpen={!!brief}
      badge={
        brief ? (
          <span className={cn(
            "rounded-full px-2 py-0.5 text-xs font-medium",
            brief.status === "generated" || brief.status === "reviewed" ? "bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300"
              : brief.status === "failed" ? "bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300"
              : "bg-muted text-muted-foreground"
          )}>{brief.status}</span>
        ) : undefined
      }
    >
      {brief && (brief.status === "generated" || brief.status === "reviewed") ? (
        <div className="space-y-3">
          {/* Opportunity score + budget */}
          <div className="flex items-center gap-4">
            <div className={cn(
              "flex h-16 w-16 items-center justify-center rounded-2xl",
              (brief.opportunity_score ?? 0) >= 70 ? "bg-emerald-50 dark:bg-emerald-950/30"
                : (brief.opportunity_score ?? 0) >= 40 ? "bg-amber-50 dark:bg-amber-950/30"
                : "bg-red-50 dark:bg-red-950/30"
            )}>
              <span className={cn(
                "text-2xl font-bold font-data",
                (brief.opportunity_score ?? 0) >= 70 ? "text-emerald-600 dark:text-emerald-400"
                  : (brief.opportunity_score ?? 0) >= 40 ? "text-amber-600 dark:text-amber-400"
                  : "text-red-600 dark:text-red-400"
              )}>{brief.opportunity_score?.toFixed(0) ?? "—"}</span>
            </div>
            <div className="space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                {brief.budget_tier && (
                  <span className={cn(
                    "rounded-md px-1.5 py-0.5 text-[10px] font-medium",
                    brief.budget_tier === "premium" ? "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300"
                      : brief.budget_tier === "high" ? "bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300"
                      : brief.budget_tier === "medium" ? "bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300"
                      : "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300"
                  )}>{brief.budget_tier.toUpperCase()}</span>
                )}
                {brief.estimated_scope && (
                  <span className="rounded-md bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                    {brief.estimated_scope.replace(/_/g, " ")}
                  </span>
                )}
                {brief.contact_priority && (
                  <span className={cn(
                    "rounded-md px-1.5 py-0.5 text-[10px] font-medium",
                    brief.contact_priority === "immediate" ? "bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300"
                      : brief.contact_priority === "high" ? "bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300"
                      : "bg-muted text-muted-foreground"
                  )}>{brief.contact_priority}</span>
                )}
              </div>
              {brief.estimated_budget_min != null && brief.estimated_budget_max != null && (
                <p className="text-sm font-mono text-foreground">USD {brief.estimated_budget_min} – {brief.estimated_budget_max}</p>
              )}
            </div>
          </div>
          {/* Contact method + call */}
          <div className="flex flex-wrap items-center gap-3 rounded-xl bg-muted/60 px-3 py-2">
            {brief.recommended_contact_method && (
              <span className="text-sm text-foreground">Contacto: <span className="font-medium">{brief.recommended_contact_method.replace(/_/g, " ")}</span></span>
            )}
            {brief.should_call && (
              <span className={cn(
                "rounded-full px-2 py-0.5 text-xs font-medium",
                brief.should_call === "yes" ? "bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300"
                  : brief.should_call === "maybe" ? "bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-300"
                  : "bg-muted text-muted-foreground"
              )}>Llamar: {brief.should_call}</span>
            )}
            {brief.demo_recommended && (
              <span className="rounded-full bg-violet-50 dark:bg-violet-950/30 px-2 py-0.5 text-xs font-medium text-violet-700 dark:text-violet-300">
                Demo recomendada
              </span>
            )}
          </div>
          {brief.call_reason && (
            <p className="text-sm text-muted-foreground"><span className="font-medium text-foreground/80">Razon de llamada:</span> {brief.call_reason}</p>
          )}
          {/* Why this lead matters */}
          {brief.why_this_lead_matters && (
            <div className="rounded-xl bg-muted/60 p-3">
              <p className="text-xs font-medium text-muted-foreground mb-1">Por que importa este lead</p>
              <p className="text-sm text-foreground/80">{brief.why_this_lead_matters}</p>
            </div>
          )}
          {/* Business signals */}
          {brief.main_business_signals && brief.main_business_signals.length > 0 && (
            <div className="rounded-xl bg-muted/60 p-3">
              <p className="text-xs font-medium text-muted-foreground mb-1">Senales de negocio</p>
              <ul className="list-disc list-inside space-y-0.5">
                {brief.main_business_signals.map((sig, i) => (
                  <li key={i} className="text-sm text-foreground/80">{sig}</li>
                ))}
              </ul>
            </div>
          )}
          {/* Digital gaps */}
          {brief.main_digital_gaps && brief.main_digital_gaps.length > 0 && (
            <div className="rounded-xl bg-muted/60 p-3">
              <p className="text-xs font-medium text-muted-foreground mb-1">Brechas digitales</p>
              <ul className="list-disc list-inside space-y-0.5">
                {brief.main_digital_gaps.map((gap, i) => (
                  <li key={i} className="text-sm text-foreground/80">{gap}</li>
                ))}
              </ul>
            </div>
          )}
          {/* Recommended angle */}
          {brief.recommended_angle && (
            <div className="rounded-xl bg-muted/60 p-3">
              <p className="text-xs font-medium text-muted-foreground mb-1">Angulo recomendado</p>
              <p className="text-sm text-foreground/80">{brief.recommended_angle}</p>
            </div>
          )}
        </div>
      ) : brief && brief.status === "failed" ? (
        <div className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400">
          <AlertCircle className="h-4 w-4" />
          {brief.error || "Error al generar brief"}
        </div>
      ) : (
        <EmptyState
          icon={Briefcase}
          title="Sin brief comercial"
          description="Genera un brief comercial para evaluar la oportunidad."
          className="py-6"
        >
          <Button
            variant="outline"
            size="sm"
            className="rounded-xl gap-1.5"
            onClick={onGenerateBrief}
            disabled={isGeneratingBrief}
          >
            {isGeneratingBrief ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Briefcase className="h-3.5 w-3.5" />}
            Generar Brief
          </Button>
        </EmptyState>
      )}
    </CollapsibleSection>
  );
}

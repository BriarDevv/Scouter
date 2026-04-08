"use client";

import { Button } from "@/components/ui/button";
import { CollapsibleSection } from "@/components/shared/collapsible-section";
import { EmptyState } from "@/components/shared/empty-state";
import { Globe, Instagram, Phone, Loader2, FileSearch, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { LeadResearchReport } from "@/types";

interface LeadDossierSectionProps {
  research: LeadResearchReport | null;
  isRunningResearch: boolean;
  onRunResearch: () => void;
}

export function LeadDossierSection({ research, isRunningResearch, onRunResearch }: LeadDossierSectionProps) {
  return (
    <CollapsibleSection
      title="Dossier"
      icon={FileSearch}
      defaultOpen={!!research}
      badge={
        research ? (
          <span className={cn(
            "rounded-full px-2 py-0.5 text-xs font-medium",
            research.status === "completed" ? "bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300"
              : research.status === "running" ? "bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300"
              : research.status === "failed" ? "bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300"
              : "bg-muted text-muted-foreground"
          )}>{research.status}</span>
        ) : undefined
      }
    >
      {research && research.status === "completed" ? (
        <div className="space-y-3">
          {/* Website */}
          <div className="flex items-center gap-3 rounded-xl bg-muted/60 px-3 py-2">
            <Globe className="h-4 w-4 text-muted-foreground shrink-0" />
            <span className="text-sm text-muted-foreground w-24 shrink-0">Website</span>
            <span className={cn("text-sm font-medium", research.website_exists ? "text-emerald-600 dark:text-emerald-400" : "text-muted-foreground")}>
              {research.website_exists ? "Existe" : "No detectado"}
            </span>
            {research.website_confidence && (
              <span className={cn(
                "rounded-md px-1.5 py-0.5 text-[10px] font-medium",
                research.website_confidence === "confirmed" ? "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300"
                  : research.website_confidence === "probable" ? "bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300"
                  : research.website_confidence === "mismatch" ? "bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300"
                  : "bg-muted text-muted-foreground"
              )}>{research.website_confidence}</span>
            )}
            {research.website_url_verified && (
              <a href={research.website_url_verified} target="_blank" rel="noopener noreferrer" className="text-xs text-foreground/70 dark:text-foreground/70 hover:text-foreground hover:underline truncate">
                {research.website_url_verified}
              </a>
            )}
          </div>
          {/* Instagram */}
          <div className="flex items-center gap-3 rounded-xl bg-muted/60 px-3 py-2">
            <Instagram className="h-4 w-4 text-muted-foreground shrink-0" />
            <span className="text-sm text-muted-foreground w-24 shrink-0">Instagram</span>
            <span className={cn("text-sm font-medium", research.instagram_exists ? "text-emerald-600 dark:text-emerald-400" : "text-muted-foreground")}>
              {research.instagram_exists ? "Existe" : "No detectado"}
            </span>
            {research.instagram_confidence && (
              <span className={cn(
                "rounded-md px-1.5 py-0.5 text-[10px] font-medium",
                research.instagram_confidence === "confirmed" ? "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300"
                  : research.instagram_confidence === "probable" ? "bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300"
                  : "bg-muted text-muted-foreground"
              )}>{research.instagram_confidence}</span>
            )}
          </div>
          {/* WhatsApp */}
          <div className="flex items-center gap-3 rounded-xl bg-muted/60 px-3 py-2">
            <Phone className="h-4 w-4 text-muted-foreground shrink-0" />
            <span className="text-sm text-muted-foreground w-24 shrink-0">WhatsApp</span>
            <span className={cn("text-sm font-medium", research.whatsapp_detected ? "text-emerald-600 dark:text-emerald-400" : "text-muted-foreground")}>
              {research.whatsapp_detected ? "Detectado" : "No detectado"}
            </span>
            {research.whatsapp_confidence && (
              <span className={cn(
                "rounded-md px-1.5 py-0.5 text-[10px] font-medium",
                research.whatsapp_confidence === "confirmed" ? "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300"
                  : "bg-muted text-muted-foreground"
              )}>{research.whatsapp_confidence}</span>
            )}
          </div>
          {/* Business description */}
          {research.business_description && (
            <div className="rounded-xl bg-muted/60 p-3">
              <p className="text-xs font-medium text-muted-foreground mb-1">Descripcion del negocio</p>
              <p className="text-sm text-foreground/80">{research.business_description}</p>
            </div>
          )}
          {/* Detected signals */}
          {research.detected_signals_json && research.detected_signals_json.length > 0 && (
            <div className="rounded-xl bg-muted/60 p-3">
              <p className="text-xs font-medium text-muted-foreground mb-2">Senales detectadas</p>
              <div className="space-y-1">
                {research.detected_signals_json.map((sig, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm">
                    <span className="font-medium text-foreground/80">{sig.type}</span>
                    <span className="text-muted-foreground">{sig.detail}</span>
                    {sig.confidence != null && (
                      <span className="text-xs text-muted-foreground">({(sig.confidence * 100).toFixed(0)}%)</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
          {/* HTML metadata */}
          {research.html_metadata_json && (
            <div className="rounded-xl bg-muted/60 p-3">
              <p className="text-xs font-medium text-muted-foreground mb-1">Metadata HTML</p>
              {research.html_metadata_json.title ? (
                <p className="text-sm text-foreground/80">Titulo: {String(research.html_metadata_json.title)}</p>
              ) : null}
              {research.html_metadata_json.description ? (
                <p className="text-sm text-foreground/80">Descripcion: {String(research.html_metadata_json.description)}</p>
              ) : null}
            </div>
          )}
          {/* Duration */}
          {research.research_duration_ms != null && (
            <p className="text-xs text-muted-foreground">
              Duracion: {(research.research_duration_ms / 1000).toFixed(1)}s
              {research.researcher_model && ` · Modelo: ${research.researcher_model}`}
            </p>
          )}
        </div>
      ) : research && research.status === "failed" ? (
        <div className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400">
          <AlertCircle className="h-4 w-4" />
          {research.error || "Error en la investigacion"}
        </div>
      ) : (
        <EmptyState
          icon={FileSearch}
          title="Sin investigacion"
          description="Ejecuta una investigacion para obtener el dossier de este lead."
          className="py-6"
        >
          <Button
            variant="outline"
            size="sm"
            className="rounded-xl gap-1.5"
            onClick={onRunResearch}
            disabled={isRunningResearch}
          >
            {isRunningResearch ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileSearch className="h-3.5 w-3.5" />}
            Investigar
          </Button>
        </EmptyState>
      )}
    </CollapsibleSection>
  );
}

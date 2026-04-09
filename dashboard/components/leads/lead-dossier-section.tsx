"use client";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/shared/empty-state";
import { Globe, Instagram, Phone, Loader2, FileSearch, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { LeadResearchReport } from "@/types";

interface LeadDossierSectionProps {
  research: LeadResearchReport | null;
  isRunningResearch: boolean;
  onRunResearch: () => void;
}

function DetectionRow({ icon: Icon, label, detected, confidence, url }: {
  icon: typeof Globe;
  label: string;
  detected: boolean | null;
  confidence: string | null;
  url?: string | null;
}) {
  return (
    <div className="flex items-center gap-3 py-2.5">
      <Icon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
      <span className="text-xs text-muted-foreground w-20 shrink-0">{label}</span>
      <span className={cn(
        "h-1.5 w-1.5 rounded-full shrink-0",
        detected ? "bg-emerald-500" : "bg-muted-foreground/30"
      )} />
      <span className={cn(
        "text-xs font-medium",
        detected ? "text-emerald-700 dark:text-emerald-300" : "text-muted-foreground"
      )}>
        {detected ? "Detectado" : "No detectado"}
      </span>
      {confidence && (
        <span className={cn(
          "rounded-full px-2 py-0.5 text-[10px] font-medium",
          confidence === "confirmed" ? "bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300"
            : confidence === "probable" ? "bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300"
            : "bg-muted text-muted-foreground"
        )}>{confidence}</span>
      )}
      {url && (
        <a href={url} target="_blank" rel="noopener noreferrer" className="text-[10px] text-muted-foreground hover:text-foreground truncate font-data underline decoration-border underline-offset-2 hover:decoration-foreground/30 transition-all ml-auto">
          {url}
        </a>
      )}
    </div>
  );
}

export function LeadDossierSection({ research, isRunningResearch, onRunResearch }: LeadDossierSectionProps) {
  if (!research || (research.status !== "completed" && research.status !== "failed")) {
    return (
      <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <FileSearch className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-semibold text-foreground font-heading">Dossier</h3>
        </div>
        <EmptyState icon={FileSearch} title="Sin investigación" description="Ejecutá una investigación para obtener el dossier de este lead." className="py-4">
          <Button variant="outline" size="sm" className="rounded-xl gap-1.5" onClick={onRunResearch} disabled={isRunningResearch}>
            {isRunningResearch ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileSearch className="h-3.5 w-3.5" />}
            Investigar
          </Button>
        </EmptyState>
      </div>
    );
  }

  if (research.status === "failed") {
    return (
      <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <FileSearch className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-semibold text-foreground font-heading">Dossier</h3>
        </div>
        <div className="flex items-center gap-2 rounded-xl bg-red-50 dark:bg-red-950/20 px-3 py-2.5 text-xs text-red-700 dark:text-red-300">
          <AlertCircle className="h-3.5 w-3.5 shrink-0" />
          {research.error || "Error en la investigación"}
        </div>
        <Button variant="outline" size="sm" className="rounded-xl gap-1.5 mt-3" onClick={onRunResearch} disabled={isRunningResearch}>
          {isRunningResearch ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileSearch className="h-3.5 w-3.5" />}
          Reintentar
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Detections */}
      <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <FileSearch className="h-4 w-4 text-muted-foreground" />
            <h3 className="text-sm font-semibold text-foreground font-heading">Detecciones</h3>
          </div>
          <span className="text-[10px] text-muted-foreground font-data">
            {research.research_duration_ms != null ? `${(research.research_duration_ms / 1000).toFixed(1)}s` : ""}
            {research.researcher_model ? ` · ${research.researcher_model}` : ""}
          </span>
        </div>
        <div className="divide-y divide-border/50">
          <DetectionRow icon={Globe} label="Website" detected={research.website_exists} confidence={research.website_confidence} url={research.website_url_verified} />
          <DetectionRow icon={Instagram} label="Instagram" detected={research.instagram_exists} confidence={research.instagram_confidence} url={research.instagram_url_verified} />
          <DetectionRow icon={Phone} label="WhatsApp" detected={research.whatsapp_detected} confidence={research.whatsapp_confidence} />
        </div>
      </div>

      {/* Business description */}
      {research.business_description != null && (
        <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Descripción del negocio</span>
          <p className="mt-2 text-sm text-muted-foreground leading-relaxed">{research.business_description}</p>
        </div>
      )}

      {/* Detected signals */}
      {research.detected_signals_json && research.detected_signals_json.length > 0 && (
        <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Señales detectadas</span>
          <div className="mt-3 space-y-1.5">
            {research.detected_signals_json.map((sig, i) => (
              <div key={i} className="flex items-center justify-between rounded-xl bg-muted px-3 py-2 text-xs">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="font-medium text-foreground">{sig.type}</span>
                  {sig.detail && <span className="text-muted-foreground truncate">— {sig.detail}</span>}
                </div>
                {sig.confidence != null && (
                  <span className="shrink-0 ml-2 text-[10px] text-muted-foreground font-data">{(sig.confidence * 100).toFixed(0)}%</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* HTML metadata */}
      {research.html_metadata_json != null && (research.html_metadata_json.title != null || research.html_metadata_json.description != null) && (
        <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Metadata HTML</span>
          <div className="mt-3 space-y-2">
            {research.html_metadata_json.title != null && (
              <div className="rounded-xl bg-muted p-3">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Título</span>
                <p className="mt-1 text-xs text-foreground">{String(research.html_metadata_json.title)}</p>
              </div>
            )}
            {research.html_metadata_json.description != null && (
              <div className="rounded-xl bg-muted p-3">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Descripción</span>
                <p className="mt-1 text-xs text-foreground">{String(research.html_metadata_json.description)}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

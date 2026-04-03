"use client";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/shared/empty-state";
import { ScoreBadge } from "@/components/shared/status-badge";
import { SIGNAL_CONFIG } from "@/lib/constants";
import { extractDomain } from "@/lib/formatters";
import {
  Globe, Instagram, Mail, Phone, MapPin, Building2,
  RefreshCw, Sparkles, Loader2, Star, Map as MapIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { Lead, LeadSignal } from "@/types";

function InfoRow({ icon: Icon, label, value, href }: { icon: typeof Globe; label: string; value: string | null; href?: string }) {
  if (!value) return null;
  return (
    <div className="flex items-center gap-3 py-2">
      <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
      <span className="text-sm text-muted-foreground w-24 shrink-0">{label}</span>
      {href ? (
        <a href={href} target="_blank" rel="noopener noreferrer" className="text-sm text-violet-600 dark:text-violet-400 hover:underline truncate font-data">
          {value}
        </a>
      ) : (
        <span className="text-sm text-foreground truncate font-data">{value}</span>
      )}
    </div>
  );
}

function SignalsList({ signals, onRunPipeline, isRunning }: { signals: LeadSignal[]; onRunPipeline: () => void; isRunning: boolean }) {
  return (
    <div className="space-y-2">
      {signals.map((s) => {
        const config = SIGNAL_CONFIG[s.signal_type];
        return (
          <div
            key={s.id}
            className={cn(
              "flex items-center gap-3 rounded-xl px-3 py-2 text-sm",
              config?.severity === "positive"
                ? "bg-emerald-50/60 dark:bg-emerald-950/20"
                : "bg-muted"
            )}
          >
            <span className="text-base">{config?.emoji || "?"}</span>
            <div>
              <span className="font-medium text-foreground/80">{config?.label || s.signal_type}</span>
              {s.detail && <span className="text-muted-foreground"> — {s.detail}</span>}
            </div>
          </div>
        );
      })}
      {signals.length === 0 && (
        <EmptyState
          icon={Sparkles}
          title="Sin señales detectadas"
          description="Ejecutá el pipeline para detectar señales."
          className="py-6"
        >
          <Button
            variant="outline"
            size="sm"
            className="rounded-xl gap-1.5"
            onClick={onRunPipeline}
            disabled={isRunning}
          >
            {isRunning ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            Ejecutar Pipeline
          </Button>
        </EmptyState>
      )}
    </div>
  );
}

interface LeadContactCardProps {
  lead: Lead;
  isRunningPipeline: boolean;
  onRunPipeline: () => void;
}

export function LeadContactCard({ lead, isRunningPipeline, onRunPipeline }: LeadContactCardProps) {
  return (
    <div className="space-y-6 lg:col-span-1">
      <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-foreground mb-3 font-heading">Datos de contacto</h3>
        <div className="divide-y divide-border/50">
          <div className="flex items-center gap-3 py-2">
            <Globe className="h-4 w-4 shrink-0 text-muted-foreground" />
            <span className="text-sm text-muted-foreground w-24 shrink-0">Website</span>
            {lead.website_url ? (
              <a href={lead.website_url} target="_blank" rel="noopener noreferrer" className="text-sm text-violet-600 dark:text-violet-400 hover:underline truncate font-data">
                {extractDomain(lead.website_url)}
              </a>
            ) : (
              <span className="text-sm text-muted-foreground/50 font-data">Sin website</span>
            )}
          </div>
          <div className="flex items-center gap-3 py-2">
            <Instagram className="h-4 w-4 shrink-0 text-muted-foreground" />
            <span className="text-sm text-muted-foreground w-24 shrink-0">Instagram</span>
            {lead.instagram_url ? (
              <a href={lead.instagram_url} target="_blank" rel="noopener noreferrer" className="text-sm text-violet-600 dark:text-violet-400 hover:underline truncate font-data">
                @{lead.instagram_url.split("/").pop()}
              </a>
            ) : (
              <span className="text-sm text-muted-foreground/50 font-data">Sin Instagram</span>
            )}
          </div>
          <InfoRow icon={Mail} label="Email" value={lead.email} href={lead.email ? `mailto:${lead.email}` : undefined} />
          <InfoRow icon={Phone} label="Teléfono" value={lead.phone} />
          <InfoRow icon={MapPin} label="Ubicación" value={lead.city ? `${lead.city}${lead.zone ? `, ${lead.zone}` : ""}` : null} />
          <InfoRow icon={MapPin} label="Dirección" value={lead.address} />
          <InfoRow icon={Building2} label="Rubro" value={lead.industry} />
          <InfoRow icon={MapIcon} label="Google Maps" value={lead.google_maps_url ? "Ver en Maps" : null} href={lead.google_maps_url || undefined} />
          {lead.rating !== null && lead.rating !== undefined && (
            <div className="flex items-center gap-3 py-2">
              <Star className="h-4 w-4 shrink-0 text-muted-foreground" />
              <span className="text-sm text-muted-foreground w-24 shrink-0">Rating</span>
              <span className="text-sm text-foreground font-data">
                {lead.rating.toFixed(1)} / 5
                {lead.review_count !== null && lead.review_count !== undefined && (
                  <span className="text-muted-foreground ml-1">({lead.review_count} reseñas)</span>
                )}
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-foreground mb-3 font-heading">Score</h3>
        <div className="flex items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
            <span className="text-2xl font-bold text-foreground font-data">{lead.score !== null ? lead.score.toFixed(0) : "—"}</span>
          </div>
          <div>
            <ScoreBadge score={lead.score} />
            <p className="mt-1 text-xs text-muted-foreground">de 100 puntos posibles</p>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-foreground mb-3 font-heading">Señales Detectadas</h3>
        <SignalsList
          signals={lead.signals ?? []}
          onRunPipeline={onRunPipeline}
          isRunning={isRunningPipeline}
        />
      </div>
    </div>
  );
}

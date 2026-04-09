"use client";

import { ScoreBadge } from "@/components/shared/status-badge";
import { API_BASE_URL, SIGNAL_CONFIG } from "@/lib/constants";
import { extractDomain } from "@/lib/formatters";
import {
  Globe, Instagram, Mail, Phone, MapPin, Building2, Star,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { Lead } from "@/types";

interface LeadSidebarProps {
  lead: Lead;
}

function ContactRow({ icon: Icon, value, href }: { icon: typeof Globe; value: string; href?: string }) {
  return (
    <div className="flex items-center gap-2 py-1">
      <Icon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
      {href ? (
        <a href={href} target="_blank" rel="noopener noreferrer" className="text-xs text-foreground/70 hover:text-foreground truncate font-data underline decoration-border underline-offset-2 hover:decoration-foreground/30 transition-all">
          {value}
        </a>
      ) : (
        <span className="text-xs text-foreground truncate font-data">{value}</span>
      )}
    </div>
  );
}

export function LeadSidebar({ lead }: LeadSidebarProps) {
  const signals = lead.signals ?? [];
  const mapsUrl = lead.google_maps_url
    || (lead.latitude && lead.longitude ? `https://www.google.com/maps?q=${lead.latitude},${lead.longitude}` : null)
    || (lead.city ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent([lead.business_name, lead.city].filter(Boolean).join(", "))}` : null);

  return (
    <div className="w-80 shrink-0 space-y-4 lg:sticky lg:top-8 self-start">
      {/* Score */}
      <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-muted">
            <span className="text-xl font-bold text-foreground font-data">
              {lead.score !== null ? lead.score.toFixed(0) : "—"}
            </span>
          </div>
          <div>
            <ScoreBadge score={lead.score} />
            <p className="mt-0.5 text-[10px] text-muted-foreground">de 100 puntos</p>
          </div>
        </div>
      </div>

      {/* Contact */}
      <div className="rounded-2xl border border-border bg-card p-4 shadow-sm space-y-1">
        <h3 className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">Contacto</h3>
        {lead.website_url && <ContactRow icon={Globe} value={extractDomain(lead.website_url) ?? lead.website_url} href={lead.website_url} />}
        {lead.instagram_url && <ContactRow icon={Instagram} value={`@${lead.instagram_url.split("/").pop()}`} href={lead.instagram_url} />}
        {lead.email && <ContactRow icon={Mail} value={lead.email} href={`mailto:${lead.email}`} />}
        {lead.phone && <ContactRow icon={Phone} value={lead.phone} />}
        {lead.city && <ContactRow icon={MapPin} value={`${lead.city}${lead.zone ? `, ${lead.zone}` : ""}`} href={mapsUrl || undefined} />}
        {lead.industry && <ContactRow icon={Building2} value={lead.industry} />}
        {lead.rating != null && (
          <div className="flex items-center gap-2 py-1">
            <Star className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
            <span className="text-xs text-foreground font-data">
              {lead.rating.toFixed(1)}/5
              {lead.review_count != null && <span className="text-muted-foreground"> ({lead.review_count})</span>}
            </span>
          </div>
        )}
      </div>

      {/* Signals */}
      {signals.length > 0 && (
        <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
          <h3 className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">Señales</h3>
          <div className="space-y-1.5">
            {signals.map((s) => {
              const config = SIGNAL_CONFIG[s.signal_type];
              return (
                <div
                  key={s.id}
                  className={cn(
                    "rounded-lg px-2.5 py-1.5 text-[10px]",
                    config?.severity === "positive"
                      ? "bg-emerald-50/60 dark:bg-emerald-950/20"
                      : "bg-muted"
                  )}
                >
                  <div className={cn(
                    "font-medium flex items-center gap-1",
                    config?.severity === "positive"
                      ? "text-emerald-700 dark:text-emerald-300"
                      : "text-muted-foreground"
                  )}>
                    <span>{config?.emoji || "?"}</span>
                    {config?.label || s.signal_type}
                  </div>
                  {s.detail && (
                    <p className="text-muted-foreground mt-0.5 leading-relaxed">{s.detail}</p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Screenshot */}
      {lead.website_url && (
        <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
          <h3 className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">Captura</h3>
          <a
            href={`${API_BASE_URL}/leads/${lead.id}/screenshot`}
            target="_blank"
            rel="noopener noreferrer"
            className="block"
          >
            <img
              src={`${API_BASE_URL}/leads/${lead.id}/screenshot`}
              alt={`Screenshot de ${lead.business_name}`}
              className="w-full max-h-40 object-cover object-top rounded-xl border border-border"
              loading="lazy"
              onError={(e) => {
                const card = (e.target as HTMLElement).closest(".rounded-2xl");
                if (card instanceof HTMLElement) card.style.display = "none";
              }}
            />
          </a>
        </div>
      )}
    </div>
  );
}

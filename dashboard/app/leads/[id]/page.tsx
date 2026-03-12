"use client";

import { use } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { StatusBadge, QualityBadge, ScoreBadge } from "@/components/shared/status-badge";
import { SIGNAL_CONFIG } from "@/lib/constants";
import { formatDate, formatDateTime, formatRelativeTime, extractDomain } from "@/lib/formatters";
import { MOCK_LEADS, MOCK_DRAFTS, MOCK_LOGS } from "@/data/mock";
import type { Lead, LeadSignal } from "@/types";
import {
  ArrowLeft, Globe, Instagram, Mail, Phone, MapPin, Building2,
  RefreshCw, FileText, CheckCircle, XCircle, Send, Calendar,
  Trophy, Ban, Sparkles, ExternalLink, Clock,
} from "lucide-react";
import { cn } from "@/lib/utils";

function InfoRow({ icon: Icon, label, value, href }: { icon: typeof Globe; label: string; value: string | null; href?: string }) {
  if (!value) return null;
  return (
    <div className="flex items-center gap-3 py-2">
      <Icon className="h-4 w-4 shrink-0 text-slate-400" />
      <span className="text-sm text-slate-500 w-24 shrink-0">{label}</span>
      {href ? (
        <a href={href} target="_blank" rel="noopener noreferrer" className="text-sm text-violet-600 hover:underline truncate font-data">
          {value}
        </a>
      ) : (
        <span className="text-sm text-slate-900 truncate font-data">{value}</span>
      )}
    </div>
  );
}

function SignalsList({ signals }: { signals: LeadSignal[] }) {
  return (
    <div className="space-y-2">
      {signals.map((s) => {
        const config = SIGNAL_CONFIG[s.signal_type];
        return (
          <div
            key={s.id}
            className={cn(
              "flex items-center gap-3 rounded-xl px-3 py-2 text-sm",
              config?.severity === "positive" ? "bg-emerald-50/60" : "bg-slate-50"
            )}
          >
            <span className="text-base">{config?.emoji || "?"}</span>
            <div>
              <span className="font-medium text-slate-700">{config?.label || s.signal_type}</span>
              {s.detail && <span className="text-slate-500"> — {s.detail}</span>}
            </div>
          </div>
        );
      })}
      {signals.length === 0 && (
        <p className="text-sm text-slate-400 py-4 text-center">Sin señales detectadas. Ejecutá el enrichment.</p>
      )}
    </div>
  );
}

export default function LeadDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const lead = MOCK_LEADS.find((l) => l.id === id);

  if (!lead) {
    return (
      <div className="space-y-6">
        <Link href="/leads" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700">
          <ArrowLeft className="h-4 w-4" /> Volver a leads
        </Link>
        <div className="rounded-2xl border border-slate-100 bg-white p-12 text-center">
          <p className="text-slate-500">Lead no encontrado</p>
        </div>
      </div>
    );
  }

  const drafts = MOCK_DRAFTS.filter((d) => d.lead_id === lead.id);
  const logs = MOCK_LOGS.filter((l) => l.lead_id === lead.id);

  return (
    <div className="space-y-6">
      {/* Back + Header */}
      <Link href="/leads" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700">
        <ArrowLeft className="h-4 w-4" /> Volver a leads
      </Link>

      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-slate-900 font-heading">{lead.business_name}</h1>
            <StatusBadge status={lead.status} />
            <QualityBadge quality={lead.quality} />
          </div>
          <div className="flex items-center gap-4 text-sm text-slate-500">
            {lead.industry && <span>{lead.industry}</span>}
            {lead.city && <span>{lead.city}{lead.zone ? `, ${lead.zone}` : ""}</span>}
            <span>Creado {formatRelativeTime(lead.created_at)}</span>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="rounded-xl gap-1.5">
            <RefreshCw className="h-3.5 w-3.5" /> Pipeline
          </Button>
          <Button variant="outline" size="sm" className="rounded-xl gap-1.5">
            <FileText className="h-3.5 w-3.5" /> Generar Draft
          </Button>
          <Button variant="outline" size="sm" className="rounded-xl gap-1.5 text-emerald-700 border-emerald-200 hover:bg-emerald-50">
            <CheckCircle className="h-3.5 w-3.5" /> Aprobar
          </Button>
        </div>
      </div>

      {/* Main grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left column: Info + Signals */}
        <div className="space-y-6 lg:col-span-1">
          {/* Contact Info */}
          <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-900 mb-3 font-heading">Datos de contacto</h3>
            <div className="divide-y divide-slate-50">
              <InfoRow icon={Globe} label="Website" value={extractDomain(lead.website_url)} href={lead.website_url || undefined} />
              <InfoRow icon={Instagram} label="Instagram" value={lead.instagram_url ? "@" + lead.instagram_url.split("/").pop() : null} href={lead.instagram_url || undefined} />
              <InfoRow icon={Mail} label="Email" value={lead.email} href={lead.email ? `mailto:${lead.email}` : undefined} />
              <InfoRow icon={Phone} label="Teléfono" value={lead.phone} />
              <InfoRow icon={MapPin} label="Ubicación" value={lead.city ? `${lead.city}${lead.zone ? `, ${lead.zone}` : ""}` : null} />
              <InfoRow icon={Building2} label="Rubro" value={lead.industry} />
            </div>
          </div>

          {/* Score */}
          <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-900 mb-3 font-heading">Score</h3>
            <div className="flex items-center gap-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-50">
                <span className="text-2xl font-bold text-slate-900 font-data">{lead.score !== null ? lead.score.toFixed(0) : "—"}</span>
              </div>
              <div>
                <ScoreBadge score={lead.score} />
                <p className="mt-1 text-xs text-slate-500">de 100 puntos posibles</p>
              </div>
            </div>
          </div>

          {/* Signals */}
          <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-900 mb-3 font-heading">Señales Detectadas</h3>
            <SignalsList signals={lead.signals} />
          </div>
        </div>

        {/* Right column: LLM Analysis + Drafts + Timeline */}
        <div className="space-y-6 lg:col-span-2">
          {/* LLM Summary */}
          {lead.llm_summary && (
            <div className="rounded-2xl border border-violet-100 bg-violet-50/30 p-5 shadow-sm">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="h-4 w-4 text-violet-600" />
                <h3 className="text-sm font-semibold text-violet-900 font-heading">Análisis IA</h3>
              </div>
              <p className="text-sm text-slate-700 leading-relaxed">{lead.llm_summary}</p>

              {lead.llm_quality_assessment && (
                <div className="mt-4 rounded-xl bg-white/60 p-3">
                  <p className="text-xs font-medium text-slate-500 mb-1">Evaluación de calidad</p>
                  <p className="text-sm text-slate-700">{lead.llm_quality_assessment}</p>
                </div>
              )}

              {lead.llm_suggested_angle && (
                <div className="mt-3 rounded-xl bg-white/60 p-3">
                  <p className="text-xs font-medium text-slate-500 mb-1">Ángulo comercial sugerido</p>
                  <p className="text-sm text-slate-700">{lead.llm_suggested_angle}</p>
                </div>
              )}
            </div>
          )}

          {!lead.llm_summary && (
            <div className="rounded-2xl border border-slate-100 bg-white p-8 text-center shadow-sm">
              <Sparkles className="mx-auto h-8 w-8 text-slate-300" />
              <p className="mt-3 text-sm font-medium text-slate-600">Análisis IA no disponible</p>
              <p className="mt-1 text-xs text-slate-400">Ejecutá el pipeline para generar el análisis con Qwen 14B</p>
              <Button variant="outline" size="sm" className="mt-4 rounded-xl gap-1.5">
                <RefreshCw className="h-3.5 w-3.5" /> Ejecutar Análisis
              </Button>
            </div>
          )}

          {/* Drafts */}
          <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-900 mb-4 font-heading">Borradores de Outreach</h3>
            {drafts.length > 0 ? (
              <div className="space-y-3">
                {drafts.map((draft) => (
                  <div key={draft.id} className="rounded-xl border border-slate-100 p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-slate-900">{draft.subject}</span>
                      <span className={cn(
                        "rounded-full px-2 py-0.5 text-xs font-medium",
                        draft.status === "pending_review" && "bg-amber-50 text-amber-700",
                        draft.status === "approved" && "bg-emerald-50 text-emerald-700",
                        draft.status === "sent" && "bg-blue-50 text-blue-700",
                        draft.status === "rejected" && "bg-red-50 text-red-700",
                      )}>
                        {draft.status === "pending_review" ? "Pendiente" : draft.status === "approved" ? "Aprobado" : draft.status === "sent" ? "Enviado" : "Rechazado"}
                      </span>
                    </div>
                    <p className="text-sm text-slate-600 whitespace-pre-line leading-relaxed">{draft.body}</p>
                    {draft.status === "pending_review" && (
                      <div className="mt-3 flex gap-2">
                        <Button size="sm" className="rounded-xl bg-emerald-600 text-white hover:bg-emerald-700 gap-1.5">
                          <CheckCircle className="h-3.5 w-3.5" /> Aprobar
                        </Button>
                        <Button variant="outline" size="sm" className="rounded-xl gap-1.5 text-red-600 border-red-200 hover:bg-red-50">
                          <XCircle className="h-3.5 w-3.5" /> Rechazar
                        </Button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-400 text-center py-6">No hay borradores generados</p>
            )}
          </div>

          {/* Timeline */}
          <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-900 mb-4 font-heading">Timeline</h3>
            {logs.length > 0 ? (
              <div className="space-y-3">
                {logs.map((log) => (
                  <div key={log.id} className="flex items-start gap-3">
                    <div className="mt-0.5 h-2 w-2 rounded-full bg-slate-300 shrink-0" />
                    <div>
                      <p className="text-sm text-slate-700">
                        <span className="font-medium capitalize">{log.action}</span>
                        {log.detail && <span className="text-slate-500"> — {log.detail}</span>}
                      </p>
                      <p className="text-xs text-slate-400 flex items-center gap-1 font-data">
                        <Clock className="h-3 w-3" />
                        {formatDateTime(log.created_at)} · {log.actor}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-400 text-center py-6">Sin actividad registrada</p>
            )}
          </div>

          {/* Notes */}
          {lead.notes && (
            <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
              <h3 className="text-sm font-semibold text-slate-900 mb-2 font-heading">Notas</h3>
              <p className="text-sm text-slate-600">{lead.notes}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

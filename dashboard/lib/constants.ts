import type { LeadQuality, LeadStatus, SignalType, DraftStatus } from "@/types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const STATUS_CONFIG: Record<LeadStatus, { label: string; color: string; bg: string }> = {
  new:         { label: "Nuevo",       color: "text-slate-700",   bg: "bg-slate-100" },
  enriched:    { label: "Enriquecido", color: "text-blue-700",    bg: "bg-blue-50" },
  scored:      { label: "Puntuado",    color: "text-indigo-700",  bg: "bg-indigo-50" },
  qualified:   { label: "Calificado",  color: "text-violet-700",  bg: "bg-violet-50" },
  draft_ready: { label: "Draft Listo", color: "text-purple-700",  bg: "bg-purple-50" },
  approved:    { label: "Aprobado",    color: "text-cyan-700",    bg: "bg-cyan-50" },
  contacted:   { label: "Contactado",  color: "text-amber-700",   bg: "bg-amber-50" },
  opened:      { label: "Abierto",     color: "text-orange-700",  bg: "bg-orange-50" },
  replied:     { label: "Respondió",   color: "text-emerald-700", bg: "bg-emerald-50" },
  meeting:     { label: "Reunión",     color: "text-teal-700",    bg: "bg-teal-50" },
  won:         { label: "Ganado",      color: "text-green-700",   bg: "bg-green-100" },
  lost:        { label: "Perdido",     color: "text-red-700",     bg: "bg-red-50" },
  suppressed:  { label: "Suprimido",   color: "text-gray-500",    bg: "bg-gray-100" },
};

export const QUALITY_CONFIG: Record<LeadQuality, { label: string; color: string; bg: string; dot: string }> = {
  high:    { label: "Alto",        color: "text-emerald-700", bg: "bg-emerald-50",  dot: "bg-emerald-500" },
  medium:  { label: "Medio",       color: "text-amber-700",   bg: "bg-amber-50",    dot: "bg-amber-500" },
  low:     { label: "Bajo",        color: "text-red-700",     bg: "bg-red-50",      dot: "bg-red-500" },
  unknown: { label: "Sin evaluar", color: "text-slate-500",   bg: "bg-slate-100",   dot: "bg-slate-400" },
};

export const SIGNAL_CONFIG: Record<SignalType, { label: string; emoji: string; severity: "positive" | "negative" | "neutral" }> = {
  no_website:        { label: "Sin website",       emoji: "🚫", severity: "positive" },
  instagram_only:    { label: "Solo Instagram",    emoji: "📸", severity: "positive" },
  outdated_website:  { label: "Web desactualizada",emoji: "🕸️", severity: "positive" },
  no_custom_domain:  { label: "Sin dominio propio",emoji: "🔗", severity: "positive" },
  no_visible_email:  { label: "Sin email visible", emoji: "📧", severity: "positive" },
  no_ssl:            { label: "Sin SSL",           emoji: "🔓", severity: "positive" },
  weak_seo:          { label: "SEO débil",         emoji: "📉", severity: "positive" },
  no_mobile_friendly:{ label: "No mobile-friendly",emoji: "📱", severity: "positive" },
  slow_load:         { label: "Carga lenta",       emoji: "🐌", severity: "positive" },
  has_website:       { label: "Tiene website",     emoji: "🌐", severity: "negative" },
  has_custom_domain: { label: "Dominio propio",    emoji: "✅", severity: "negative" },
};

export const DRAFT_STATUS_CONFIG: Record<DraftStatus, { label: string; color: string; bg: string }> = {
  pending_review: { label: "Pendiente",  color: "text-amber-700",   bg: "bg-amber-50" },
  approved:       { label: "Aprobado",   color: "text-emerald-700", bg: "bg-emerald-50" },
  rejected:       { label: "Rechazado",  color: "text-red-700",     bg: "bg-red-50" },
  sent:           { label: "Enviado",    color: "text-blue-700",    bg: "bg-blue-50" },
};

export const PIPELINE_STAGES: LeadStatus[] = [
  "new", "enriched", "scored", "qualified", "draft_ready",
  "approved", "contacted", "opened", "replied", "meeting", "won",
];

export const SCORE_THRESHOLDS = {
  high: 60,
  medium: 30,
};

export function getScoreLevel(score: number | null): "high" | "medium" | "low" {
  if (score === null) return "low";
  if (score >= SCORE_THRESHOLDS.high) return "high";
  if (score >= SCORE_THRESHOLDS.medium) return "medium";
  return "low";
}

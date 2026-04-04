import type { LLMSettings } from "@/types";
import {
  BrainCircuit,
  Search,
  BarChart3,
  Sparkles,
  FileText,
  CheckCircle2,
  Zap,
} from "lucide-react";

export const STEP_CONFIG: Record<string, { label: string; icon: typeof BrainCircuit; description: string }> = {
  pipeline_dispatch: { label: "Iniciando pipeline",    icon: Zap,          description: "Coordinando los pasos del pipeline completo" },
  enrichment:        { label: "Enriqueciendo",         icon: Search,       description: "Buscando información pública del negocio" },
  scoring:           { label: "Puntuando",              icon: BarChart3,    description: "Calculando score basado en señales detectadas" },
  analysis:          { label: "Analizando con IA",     icon: Sparkles,     description: "Generando resumen, evaluación y ángulo comercial" },
  draft_generation:  { label: "Generando draft",       icon: FileText,     description: "Escribiendo borrador de email personalizado" },
  lead_review:       { label: "Review de lead",        icon: Sparkles,     description: "IA evaluando calidad y fit del lead" },
  draft_review:      { label: "Review de draft",       icon: Sparkles,     description: "IA revisando calidad del borrador" },
  inbound_reply_review:  { label: "Clasificando reply",  icon: Sparkles,   description: "IA clasificando respuesta inbound recibida" },
  reply_draft_review:    { label: "Generando respuesta", icon: FileText,   description: "IA redactando respuesta al reply del lead" },
  completed:         { label: "Completado",             icon: CheckCircle2, description: "Todos los pasos finalizaron correctamente" },
};

export const REVIEWER_STEPS = new Set(["lead_review", "draft_review"]);
export const NO_LLM_STEPS = new Set(["enrichment", "scoring", "pipeline_dispatch", "completed"]);

export function getStepConfig(step: string | null | undefined) {
  if (!step) return { label: "Procesando", icon: BrainCircuit, description: "Tarea en curso" };
  return STEP_CONFIG[step] ?? { label: step.replace(/_/g, " "), icon: BrainCircuit, description: "" };
}

export function getModelForStep(step: string | null | undefined, llm: LLMSettings | null): string | null {
  if (!step) return null;
  if (NO_LLM_STEPS.has(step)) return "_system";
  if (!llm) return null;
  if (REVIEWER_STEPS.has(step)) return llm.reviewer_model;
  return llm.executor_model;
}

export function formatModelShort(model: string): string {
  const match = model.match(/:(\d+[bB])/);
  if (match) return match[1].toUpperCase();
  return model.split(":").pop()?.toUpperCase() || model;
}

export function isActive(status: string) {
  return ["running", "started", "queued", "pending", "retrying"].includes(status);
}

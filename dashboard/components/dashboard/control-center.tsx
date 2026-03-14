"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  Brain,
  Database,
  Loader2,
  Mail,
  MessageCircle,
  Play,
  Power,
  RefreshCw,
  Server,
  ShieldCheck,
  Sparkles,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { sileo } from "sileo";
import {
  getSystemHealth,
  getOperationalSettings,
  updateOperationalSettings,
  getLeads,
  runFullPipeline,
} from "@/lib/api/client";
import type { HealthComponent, OperationalSettings } from "@/types";

// ─── Types ──────────────────────────────────────────────────────────────────

interface FeatureToggle {
  key: keyof OperationalSettings;
  label: string;
  hint: string;
  icon: React.ElementType;
  category: "ia" | "mail" | "whatsapp";
  dependsOn?: keyof OperationalSettings;
}

const FEATURES: FeatureToggle[] = [
  {
    key: "reply_assistant_enabled",
    label: "Reply Assistant",
    hint: "Genera borradores de respuesta para mensajes inbound",
    icon: Sparkles,
    category: "ia",
  },
  {
    key: "reviewer_enabled",
    label: "Reviewer IA",
    hint: "Revisa y clasifica drafts/labels con el modelo de 27B",
    icon: ShieldCheck,
    category: "ia",
  },
  {
    key: "auto_classify_inbound",
    label: "Auto-clasificar inbound",
    hint: "Clasifica replies entrantes automaticamente",
    icon: Brain,
    category: "ia",
  },
  {
    key: "mail_enabled",
    label: "Envio de mails",
    hint: "Habilita el envio de outreach por SMTP",
    icon: Mail,
    category: "mail",
  },
  {
    key: "require_approved_drafts",
    label: "Requiere aprobacion",
    hint: "Los drafts necesitan revision antes de envio",
    icon: ShieldCheck,
    category: "mail",
  },
  {
    key: "whatsapp_conversational_enabled",
    label: "WhatsApp comandos",
    hint: "Recibir y responder comandos por WhatsApp",
    icon: MessageCircle,
    category: "whatsapp",
  },
  {
    key: "whatsapp_openclaw_enrichment",
    label: "OpenClaw chat",
    hint: "Responde mensajes libres con IA (4b)",
    icon: Brain,
    category: "whatsapp",
    dependsOn: "whatsapp_conversational_enabled",
  },
];

// ─── Helpers ────────────────────────────────────────────────────────────────

function statusColor(status: string): string {
  if (status === "ok") return "bg-emerald-500";
  if (status === "degraded") return "bg-yellow-500";
  return "bg-red-500";
}

function statusGlow(status: string): string {
  if (status === "ok") return "shadow-[0_0_8px_rgba(34,197,94,0.6)]";
  if (status === "degraded") return "shadow-[0_0_8px_rgba(234,179,8,0.6)]";
  return "shadow-[0_0_8px_rgba(239,68,68,0.6)]";
}

function componentIcon(name: string) {
  switch (name) {
    case "database": return Database;
    case "redis": return Server;
    case "ollama": return Brain;
    case "celery": return Activity;
    default: return Zap;
  }
}

function componentLabel(name: string) {
  switch (name) {
    case "database": return "PostgreSQL";
    case "redis": return "Redis";
    case "ollama": return "Ollama";
    case "celery": return "Celery";
    default: return name;
  }
}

// ─── Component ──────────────────────────────────────────────────────────────

export function ControlCenter() {
  const [health, setHealth] = useState<HealthComponent[]>([]);
  const [settings, setSettings] = useState<OperationalSettings | null>(null);
  const [loadingHealth, setLoadingHealth] = useState(true);
  const [loadingSettings, setLoadingSettings] = useState(true);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [runningPipeline, setRunningPipeline] = useState(false);
  const [pipelineResult, setPipelineResult] = useState<string | null>(null);

  const loadHealth = useCallback(async () => {
    setLoadingHealth(true);
    try {
      const data = await getSystemHealth();
      setHealth(data.components);
    } catch {
      setHealth([]);
    } finally {
      setLoadingHealth(false);
    }
  }, []);

  const loadSettings = useCallback(async () => {
    setLoadingSettings(true);
    try {
      const data = await getOperationalSettings();
      setSettings(data);
    } catch {
      // Settings not available
    } finally {
      setLoadingSettings(false);
    }
  }, []);

  useEffect(() => {
    loadHealth();
    loadSettings();
  }, [loadHealth, loadSettings]);

  // Auto-refresh health every 30s
  useEffect(() => {
    const interval = setInterval(loadHealth, 30_000);
    return () => clearInterval(interval);
  }, [loadHealth]);

  async function toggleFeature(key: keyof OperationalSettings, value: boolean) {
    if (!settings) return;
    setSavingKey(key);
    try {
      const updated = await updateOperationalSettings({ [key]: value });
      setSettings(updated);
      sileo.success({
        title: value ? "Activado" : "Desactivado",
        description: FEATURES.find((f) => f.key === key)?.label,
      });
    } catch (err) {
      sileo.error({
        title: "Error al cambiar configuracion",
        description: err instanceof Error ? err.message : "Error desconocido",
      });
    } finally {
      setSavingKey(null);
    }
  }

  async function handleRunPipeline() {
    setRunningPipeline(true);
    setPipelineResult(null);
    try {
      // Get first lead to run pipeline on
      const leadsRes = await getLeads({ page: 1, page_size: 1, status: "new" });
      if (!leadsRes.items.length) {
        sileo.error({ title: "No hay leads nuevos para procesar" });
        return;
      }

      const lead = leadsRes.items[0];
      const result = await runFullPipeline(lead.id);
      setPipelineResult(result.task_id);
      sileo.success({
        title: "Pipeline iniciado",
        description: `Lead: ${lead.business_name ?? lead.id.slice(0, 8)}`,
      });
    } catch (err) {
      sileo.error({
        title: "Error al iniciar pipeline",
        description: err instanceof Error ? err.message : "Error desconocido",
      });
    } finally {
      setRunningPipeline(false);
    }
  }

  const ollamaOk = health.find((c) => c.name === "ollama")?.status === "ok";
  const celeryOk = health.find((c) => c.name === "celery")?.status === "ok";
  const allOk = health.length > 0 && health.every((c) => c.status === "ok");

  return (
    <div className="rounded-2xl border border-border bg-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-5 py-3">
        <div className="flex items-center gap-3">
          <div className={cn(
            "flex h-8 w-8 items-center justify-center rounded-lg",
            allOk ? "bg-emerald-50 dark:bg-emerald-950/40" : "bg-amber-50 dark:bg-amber-950/40"
          )}>
            <Power className={cn("h-4 w-4", allOk ? "text-emerald-600 dark:text-emerald-400" : "text-amber-600 dark:text-amber-400")} />
          </div>
          <div>
            <h3 className="text-sm font-bold text-foreground">Centro de Control</h3>
            <p className="text-[11px] text-muted-foreground">
              {allOk ? "Todos los servicios operativos" : "Algunos servicios con problemas"}
            </p>
          </div>
        </div>
        <button
          onClick={() => { loadHealth(); loadSettings(); }}
          className="rounded-lg p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          title="Actualizar estado"
        >
          <RefreshCw className={cn("h-4 w-4", loadingHealth && "animate-spin")} />
        </button>
      </div>

      <div className="grid gap-0 lg:grid-cols-3">
        {/* ── Col 1: System Health ──────────────────────────── */}
        <div className="border-b lg:border-b-0 lg:border-r border-border p-4 space-y-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Infraestructura
          </p>

          {loadingHealth ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Chequeando...
            </div>
          ) : health.length === 0 ? (
            <p className="text-sm text-muted-foreground">No se pudo conectar al backend</p>
          ) : (
            <div className="grid grid-cols-2 gap-2">
              {health.map((comp) => {
                const Icon = componentIcon(comp.name);
                return (
                  <div
                    key={comp.name}
                    className="flex items-center gap-2.5 rounded-lg bg-muted/50 px-3 py-2"
                  >
                    <span className={cn(
                      "inline-block h-2 w-2 rounded-full flex-shrink-0",
                      statusColor(comp.status),
                      statusGlow(comp.status),
                    )} />
                    <Icon className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                    <div className="min-w-0">
                      <p className="text-xs font-medium text-foreground truncate">
                        {componentLabel(comp.name)}
                      </p>
                      {comp.latency_ms != null && (
                        <p className="text-[10px] text-muted-foreground tabular-nums">
                          {comp.latency_ms.toFixed(0)}ms
                        </p>
                      )}
                      {comp.error && (
                        <p className="text-[10px] text-red-500 truncate" title={comp.error}>
                          {comp.error.slice(0, 30)}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Pipeline trigger */}
          <div className="pt-1">
            <button
              onClick={handleRunPipeline}
              disabled={runningPipeline || !celeryOk}
              className={cn(
                "flex w-full items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition-all",
                celeryOk
                  ? "bg-violet-600 text-white hover:bg-violet-700 active:scale-[0.98]"
                  : "bg-muted text-muted-foreground cursor-not-allowed",
                runningPipeline && "opacity-70"
              )}
            >
              {runningPipeline ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              {runningPipeline ? "Procesando..." : "Iniciar Pipeline"}
            </button>
            {!celeryOk && (
              <p className="mt-1 text-[10px] text-amber-500 text-center">
                Celery debe estar corriendo para iniciar pipelines
              </p>
            )}
            {pipelineResult && (
              <p className="mt-1 text-[10px] text-emerald-500 text-center tabular-nums">
                Task: {pipelineResult.slice(0, 12)}...
              </p>
            )}
          </div>
        </div>

        {/* ── Col 2: IA Features ──────────────────────────── */}
        <div className="border-b lg:border-b-0 lg:border-r border-border p-4 space-y-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Inteligencia Artificial
          </p>

          {loadingSettings || !settings ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Cargando...
            </div>
          ) : (
            <div className="space-y-1">
              {FEATURES.filter((f) => f.category === "ia").map((feat) => {
                const enabled = Boolean(settings[feat.key]);
                const saving = savingKey === feat.key;
                const depDisabled = feat.dependsOn && !settings[feat.dependsOn];

                return (
                  <button
                    key={feat.key}
                    onClick={() => toggleFeature(feat.key, !enabled)}
                    disabled={saving || Boolean(depDisabled)}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left transition-all",
                      enabled
                        ? "bg-violet-50 dark:bg-violet-950/30"
                        : "bg-muted/30 hover:bg-muted/50",
                      depDisabled && "opacity-40 cursor-not-allowed"
                    )}
                  >
                    <feat.icon className={cn(
                      "h-4 w-4 flex-shrink-0",
                      enabled ? "text-violet-600 dark:text-violet-400" : "text-muted-foreground"
                    )} />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-foreground">{feat.label}</p>
                      <p className="text-[10px] text-muted-foreground truncate">{feat.hint}</p>
                    </div>
                    <div className={cn(
                      "flex h-5 w-9 flex-shrink-0 items-center rounded-full px-0.5 transition-colors",
                      enabled ? "bg-violet-600" : "bg-muted-foreground/30"
                    )}>
                      <div className={cn(
                        "h-4 w-4 rounded-full bg-white shadow-sm transition-transform",
                        enabled ? "translate-x-4" : "translate-x-0"
                      )} />
                    </div>
                    {saving && <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />}
                  </button>
                );
              })}

              {!ollamaOk && (
                <p className="text-[10px] text-amber-500 px-3 pt-1">
                  Ollama no esta corriendo — los features de IA no van a funcionar
                </p>
              )}
            </div>
          )}
        </div>

        {/* ── Col 3: Channels ─────────────────────────────── */}
        <div className="p-4 space-y-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Canales
          </p>

          {loadingSettings || !settings ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Cargando...
            </div>
          ) : (
            <div className="space-y-1">
              {FEATURES.filter((f) => f.category === "mail" || f.category === "whatsapp").map((feat) => {
                const enabled = Boolean(settings[feat.key]);
                const saving = savingKey === feat.key;
                const depDisabled = feat.dependsOn && !settings[feat.dependsOn];

                return (
                  <button
                    key={feat.key}
                    onClick={() => toggleFeature(feat.key, !enabled)}
                    disabled={saving || Boolean(depDisabled)}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left transition-all",
                      enabled
                        ? "bg-emerald-50 dark:bg-emerald-950/30"
                        : "bg-muted/30 hover:bg-muted/50",
                      depDisabled && "opacity-40 cursor-not-allowed"
                    )}
                  >
                    <feat.icon className={cn(
                      "h-4 w-4 flex-shrink-0",
                      enabled ? "text-emerald-600 dark:text-emerald-400" : "text-muted-foreground"
                    )} />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-foreground">{feat.label}</p>
                      <p className="text-[10px] text-muted-foreground truncate">{feat.hint}</p>
                    </div>
                    <div className={cn(
                      "flex h-5 w-9 flex-shrink-0 items-center rounded-full px-0.5 transition-colors",
                      enabled ? "bg-emerald-600" : "bg-muted-foreground/30"
                    )}>
                      <div className={cn(
                        "h-4 w-4 rounded-full bg-white shadow-sm transition-transform",
                        enabled ? "translate-x-4" : "translate-x-0"
                      )} />
                    </div>
                    {saving && <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

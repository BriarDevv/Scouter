"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Brain,
  Loader2,
  Mail,
  MessageCircle,
  Play,
  Power,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Square,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { sileo } from "sileo";
import {
  getOperationalSettings,
  updateOperationalSettings,
  getTerritories,
} from "@/lib/api/client";
import { API_BASE_URL } from "@/lib/constants";
import type { HealthComponent, OperationalSettings, TerritoryWithStats } from "@/types";

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

// ─── Component ──────────────────────────────────────────────────────────────

interface ControlCenterProps {
  health: HealthComponent[];
}

const LS_PIPELINE_KEY = "cs:pipeline_task_id";
const LS_CRAWL_TERRITORY_KEY = "cs:crawl_territory_id";

export function ControlCenter({ health }: ControlCenterProps) {
  const [settings, setSettings] = useState<OperationalSettings | null>(null);
  const [loadingSettings, setLoadingSettings] = useState(true);
  const isInitialSettings = useRef(true);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [pipelineStatus, setPipelineStatus] = useState<"idle" | "running" | "done" | "error" | "stopping">("idle");
  const [pipelineProgress, setPipelineProgress] = useState<string | null>(null);
  const [territories, setTerritories] = useState<TerritoryWithStats[]>([]);
  const [selectedTerritoryId, setSelectedTerritoryId] = useState<string>("");
  const [crawlStatus, setCrawlStatus] = useState<"idle" | "running" | "done" | "error">("idle");
  const [crawlProgress, setCrawlProgress] = useState<string | null>(null);
  const [crawlTaskId, setCrawlTaskId] = useState<string | null>(null);

  const loadSettings = useCallback(async () => {
    if (isInitialSettings.current) setLoadingSettings(true);
    try {
      const data = await getOperationalSettings();
      setSettings(data);
    } catch {
      // Settings not available
    } finally {
      setLoadingSettings(false);
      isInitialSettings.current = false;
    }
  }, []);

  // Check batch pipeline status on mount + poll when running
  useEffect(() => {
    let active = true;
    async function checkPipeline() {
      try {
        const res = await fetch(`${API_BASE_URL}/pipelines/batch/status`);
        const data = await res.json();
        if (!active) return;
        if (data.status === "running" || data.status === "stopping") {
          setPipelineStatus(data.status === "stopping" ? "stopping" : "running");
          setPipelineProgress(data.current_lead
            ? `${data.current_lead} (${data.processed ?? 0}/${data.total ?? 0}) — ${data.current_step ?? ""}`
            : "Iniciando...");
        } else if (data.status === "done") {
          setPipelineStatus("done");
          setPipelineProgress(`Listo — ${data.processed ?? 0} leads procesados`);
        }
      } catch { /* ignore */ }
    }
    checkPipeline();
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (pipelineStatus !== "running") return;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/pipelines/batch/status`);
        const data = await res.json();
        if (data.status === "done") {
          setPipelineStatus("done");
          const crawlNote = data.crawl_rounds ? ` (${data.crawl_rounds} crawls, ${data.leads_from_crawl ?? 0} encontrados)` : "";
          setPipelineProgress(`Listo — ${data.processed ?? 0} leads procesados${crawlNote}`);
          sileo.success({ title: `Pipeline completado: ${data.processed ?? 0} leads` });
        } else if (data.status === "error") {
          setPipelineStatus("error");
          setPipelineProgress(data.error ?? "Error");
          sileo.error({ title: data.error ?? "Error en pipeline" });
        } else if (data.status === "stopped") {
          setPipelineStatus("idle");
          setPipelineProgress(null);
          sileo.success({ title: "Pipeline detenido" });
        } else if (data.status === "running") {
          const step = data.current_step ?? "";
          const crawlInfo = data.crawl_rounds ? ` | crawl #${data.crawl_rounds}` : "";
          if (step === "crawling") {
            setPipelineProgress(`Buscando leads — ${data.current_lead ?? "crawling..."}${crawlInfo}`);
          } else if (data.current_lead) {
            setPipelineProgress(`${data.current_lead} (${data.processed ?? 0}/${data.total ?? 0}) — ${step}${crawlInfo}`);
          } else {
            setPipelineProgress("Iniciando...");
          }
        }
      } catch { /* ignore */ }
    }, 2000);
    return () => clearInterval(interval);
  }, [pipelineStatus]);

  useEffect(() => {
    loadSettings();
    getTerritories()
      .then((data) => {
        setTerritories(data);
        if (data.length > 0) {
          const savedTerritoryId = localStorage.getItem(LS_CRAWL_TERRITORY_KEY) || data[0].id;
          const territoryExists = data.some((t) => t.id === savedTerritoryId);
          const tid = territoryExists ? savedTerritoryId : data[0].id;
          setSelectedTerritoryId(tid);
          fetch(`${API_BASE_URL}/crawl/territory/${tid}/status`)
            .then((r) => r.json())
            .then((s) => {
              if (s.status === "running") {
                setCrawlStatus("running");
                setCrawlTaskId(s.task_id ?? null);
                setCrawlProgress(s.current_city ? `${s.current_city} (${s.current_city_idx ?? 0}/${s.total_cities ?? 0})` : "Iniciando...");
              }
            })
            .catch(() => {});
        }
      })
      .catch(() => {});
  }, [loadSettings]);

  // Poll crawl status when running
  useEffect(() => {
    if (crawlStatus !== "running" || !selectedTerritoryId) return;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/crawl/territory/${selectedTerritoryId}/status`);
        const data = await res.json();
        if (data.task_id) setCrawlTaskId(data.task_id);
        if (data.status === "done") {
          setCrawlStatus("done");
          setCrawlProgress(`Listo — ${data.leads_created ?? 0} leads nuevos`);
          localStorage.removeItem(LS_CRAWL_TERRITORY_KEY);
          sileo.success({ title: `Crawl completado: ${data.leads_created ?? 0} leads nuevos` });
        } else if (data.status === "error") {
          setCrawlStatus("error");
          setCrawlProgress(data.error ?? "Error");
          localStorage.removeItem(LS_CRAWL_TERRITORY_KEY);
          sileo.error({ title: data.error ?? "Error en el crawl" });
        } else if (data.status === "running") {
          setCrawlProgress(`${data.current_city ?? "..."} (${data.current_city_idx ?? 0}/${data.total_cities ?? 0})`);
        }
      } catch { /* ignore */ }
    }, 2000);
    return () => clearInterval(interval);
  }, [crawlStatus, selectedTerritoryId]);

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
    try {
      const res = await fetch(`${API_BASE_URL}/pipelines/batch`, { method: "POST" });
      const data = await res.json();
      if (data.ok) {
        setPipelineStatus("running");
        setPipelineProgress("Iniciando...");
        sileo.success({ title: "Pipeline iniciado", description: data.message });
      } else {
        sileo.error({ title: data.message ?? "Error al iniciar pipeline" });
      }
    } catch {
      sileo.error({ title: "Error de conexión al iniciar pipeline" });
    }
  }

  async function handleStopPipeline() {
    try {
      await fetch(`${API_BASE_URL}/pipelines/batch/stop`, { method: "POST" });
      setPipelineStatus("stopping");
      setPipelineProgress("Deteniendo...");
    } catch {
      sileo.error({ title: "Error al detener pipeline" });
    }
  }

  async function handleStartCrawl() {
    if (!selectedTerritoryId) return;
    try {
      const res = await fetch(`${API_BASE_URL}/crawl/territory`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ territory_id: selectedTerritoryId }),
      });
      const data = await res.json();
      if (data.ok) {
        setCrawlStatus("running");
        setCrawlProgress("Iniciando...");
        setCrawlTaskId(data.task_id ?? null);
        localStorage.setItem(LS_CRAWL_TERRITORY_KEY, selectedTerritoryId);
        sileo.success({ title: "Crawl iniciado", description: data.message });
      } else {
        sileo.error({ title: data.message ?? "Error al iniciar crawl" });
      }
    } catch {
      sileo.error({ title: "Error de conexión al iniciar crawl" });
    }
  }

  async function handleStopCrawl() {
    if (!selectedTerritoryId) return;
    try {
      // Revoke the Celery task if we have its ID
      if (crawlTaskId) {
        await fetch(`${API_BASE_URL}/tasks/${crawlTaskId}/revoke`, { method: "POST" });
      }
      // Clear Redis status
      await fetch(`${API_BASE_URL}/crawl/territory/${selectedTerritoryId}/stop`, { method: "POST" });
      setCrawlStatus("idle");
      setCrawlProgress(null);
      setCrawlTaskId(null);
      localStorage.removeItem(LS_CRAWL_TERRITORY_KEY);
      sileo.success({ title: "Crawl detenido" });
    } catch {
      sileo.error({ title: "Error al detener crawl" });
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
          onClick={() => { loadSettings(); }}
          className="rounded-lg p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          title="Actualizar estado"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      <div className="grid gap-0 lg:grid-cols-3">
        {/* ── Col 1: Operations ──────────────────────────── */}
        <div className="border-b lg:border-b-0 lg:border-r border-border p-4 space-y-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Operaciones
          </p>

          {/* Pipeline toggle */}
          <div className="pt-1 space-y-1.5">
            {pipelineStatus !== "running" && pipelineStatus !== "stopping" ? (
              <button
                onClick={handleRunPipeline}
                disabled={!celeryOk}
                className={cn(
                  "flex w-full items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition-all",
                  celeryOk
                    ? "bg-violet-600 text-white hover:bg-violet-700 active:scale-[0.98]"
                    : "bg-muted text-muted-foreground cursor-not-allowed"
                )}
              >
                <Play className="h-4 w-4" />
                Iniciar Pipeline
              </button>
            ) : (
              <button
                onClick={handleStopPipeline}
                disabled={pipelineStatus === "stopping"}
                className={cn(
                  "flex w-full items-center justify-center gap-2 rounded-xl bg-red-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-red-700 active:scale-[0.98] transition-all",
                  pipelineStatus === "stopping" && "opacity-70"
                )}
              >
                <Square className="h-4 w-4" />
                {pipelineStatus === "stopping" ? "Deteniendo..." : "Detener Pipeline"}
              </button>
            )}
            {!celeryOk && (
              <p className="text-[10px] text-amber-500 text-center">
                Celery debe estar corriendo
              </p>
            )}
            {pipelineProgress && (
              <p className={cn(
                "text-[10px] text-center",
                pipelineStatus === "running" ? "text-violet-500" : pipelineStatus === "done" ? "text-emerald-500" : "text-muted-foreground"
              )}>
                {pipelineStatus === "running" && <Loader2 className="inline h-3 w-3 animate-spin mr-1" />}
                {pipelineProgress}
              </p>
            )}
          </div>

          {/* Crawl toggle */}
          <div className="pt-1 space-y-1.5">
            {territories.length > 0 && (
              <select
                value={selectedTerritoryId}
                onChange={(e) => {
                  setSelectedTerritoryId(e.target.value);
                  setCrawlStatus("idle");
                  setCrawlProgress(null);
                }}
                disabled={crawlStatus === "running"}
                className="w-full appearance-none rounded-lg border border-border bg-muted px-2.5 py-1.5 text-xs text-foreground outline-none disabled:opacity-50"
              >
                {territories.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name} ({t.cities?.length ?? 0} ciudades)
                  </option>
                ))}
              </select>
            )}
            {crawlStatus !== "running" ? (
              <button
                onClick={handleStartCrawl}
                disabled={!celeryOk || !selectedTerritoryId}
                className={cn(
                  "flex w-full items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition-all",
                  celeryOk && selectedTerritoryId
                    ? "bg-emerald-600 text-white hover:bg-emerald-700 active:scale-[0.98]"
                    : "bg-muted text-muted-foreground cursor-not-allowed"
                )}
              >
                <Search className="h-4 w-4" />
                Iniciar Crawl
              </button>
            ) : (
              <button
                onClick={handleStopCrawl}
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-red-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-red-700 active:scale-[0.98] transition-all"
              >
                <Square className="h-4 w-4" />
                Detener Crawl
              </button>
            )}
            {crawlProgress && (
              <p className={cn(
                "text-[10px] text-center",
                crawlStatus === "running" ? "text-violet-500" : crawlStatus === "done" ? "text-emerald-500" : "text-red-500"
              )}>
                {crawlStatus === "running" && <Loader2 className="inline h-3 w-3 animate-spin mr-1" />}
                {crawlProgress}
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

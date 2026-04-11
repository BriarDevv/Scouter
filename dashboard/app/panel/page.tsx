"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Loader2,
  Play,
  Square,
  RefreshCw,
  ChevronDown,
  Database,
  HardDrive,
} from "lucide-react";
import { sileo } from "sileo";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useSystemHealth } from "@/lib/hooks/use-system-health";
import { useVisibleInterval } from "@/lib/hooks/use-visible-interval";
import { useApi } from "@/lib/hooks/use-swr-fetch";
import {
  getOperationalSettings,
  updateOperationalSettings,
  setRuntimeMode,
  apiFetch,
} from "@/lib/api/client";
import { formatPercent, formatNumber } from "@/lib/formatters";
import { StatsGrid } from "@/components/dashboard/stats-grid";
import { PipelineFunnel } from "@/components/dashboard/pipeline-funnel";
import { AreaChartCard } from "@/components/charts/area-chart-card";
import { IndustryChart } from "@/components/dashboard/industry-chart";
import { RecentActivity } from "@/components/dashboard/recent-activity";
import { TerritorySummary } from "@/components/dashboard/territory-summary";
import { FeatureToggleList, type FeatureToggle } from "@/components/dashboard/feature-toggle-list";
import { SkeletonStatCard, SkeletonCard } from "@/components/shared/skeleton";
import type {
  DashboardStats,
  IndustryBreakdown,
  HealthComponent,
  OperationalSettings,
  OutreachLog,
  PipelineStage,
  RuntimeMode,
  TimeSeriesPoint,
} from "@/types";
import {
  Bell,
  Brain,
  Inbox,
  Mail,
  MessageCircle,
  Send,
  ShieldCheck,
  Sparkles,
  Wand2,
  Zap,
} from "lucide-react";

// ─── Pipeline batch types ──────────────────────────────

interface PipelineBatchStatus {
  status: string;
  ok?: boolean;
  message?: string;
  task_id?: string;
  processed?: number;
  total?: number;
  current_lead?: string | null;
  current_step?: string;
  error?: string;
  crawl_rounds?: number;
  leads_from_crawl?: number;
}

// ─── Feature definitions ───────────────────────────────

const IA_FEATURES: FeatureToggle[] = [
  { key: "reply_assistant_enabled", label: "Reply Assistant", hint: "Borradores de respuesta automaticos", icon: Wand2, category: "ia" },
  { key: "reviewer_enabled", label: "Reviewer IA", hint: "Revision con modelo de 27B", icon: ShieldCheck, category: "ia" },
  { key: "auto_classify_inbound", label: "Auto-clasificar inbound", hint: "Clasifica replies automaticamente", icon: Brain, category: "ia" },
  { key: "whatsapp_agent_enabled", label: "Mote WhatsApp", hint: "Mote responde por WhatsApp", icon: Sparkles, category: "ia" },
  { key: "telegram_agent_enabled", label: "Mote Telegram", hint: "Mote responde por Telegram", icon: Sparkles, category: "ia" },
  { key: "low_resource_mode", label: "Low Resources", hint: "Modelos livianos, menos VRAM", icon: Zap, category: "ia" },
];

const CHANNEL_FEATURES: FeatureToggle[] = [
  { key: "mail_enabled", label: "Mail outbound", hint: "Outreach por SMTP", icon: Send, category: "mail" },
  { key: "mail_inbound_sync_enabled", label: "Mail inbound", hint: "Sync bandeja de entrada", icon: Inbox, category: "mail" },
  { key: "require_approved_drafts", label: "Requiere aprobacion", hint: "Revision antes de envio", icon: ShieldCheck, category: "mail" },
  { key: "whatsapp_outreach_enabled", label: "WhatsApp outreach", hint: "Drafts de WhatsApp en pipeline", icon: MessageCircle, category: "whatsapp" },
  { key: "notifications_enabled", label: "Notificaciones", hint: "Alertas globales del sistema", icon: Bell, category: "whatsapp" },
  { key: "telegram_alerts_enabled", label: "Telegram alertas", hint: "Notificaciones por Telegram", icon: Bell, category: "whatsapp" },
];

// ─── Page ──────────────────────────────────────────────

export default function PanelPage() {
  // Health
  const { components: health, loading: healthLoading, refresh: refreshHealth } = useSystemHealth();

  // Dashboard data
  const { data: stats, isLoading: statsLoading, error: statsError, mutate: mutateStats } = useApi<DashboardStats>("/dashboard/stats");
  const { data: pipeline, mutate: mutatePipeline } = useApi<PipelineStage[]>("/dashboard/pipeline");
  const { data: timeSeries, mutate: mutateTimeSeries } = useApi<TimeSeriesPoint[]>("/dashboard/time-series?days=30");
  const { data: industryBreakdown, mutate: mutateIndustry } = useApi<IndustryBreakdown[]>("/performance/industry");
  const { data: logs, mutate: mutateLogs } = useApi<OutreachLog[]>("/outreach/logs?limit=8");

  // Pipeline state
  const [pipelineStatus, setPipelineStatus] = useState<"idle" | "running" | "done" | "error" | "stopping">("idle");
  const [pipelineProgress, setPipelineProgress] = useState<string | null>(null);

  // Settings & runtime
  const [settings, setSettings] = useState<OperationalSettings | null>(null);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [runtimeMode, setRuntimeModeState] = useState<RuntimeMode>("safe");
  const [savingMode, setSavingMode] = useState(false);
  const isInitialSettings = useRef(true);
  const [loadingSettings, setLoadingSettings] = useState(true);

  // ── Load settings ──
  const loadSettings = useCallback(async () => {
    if (isInitialSettings.current) setLoadingSettings(true);
    try {
      const data = await getOperationalSettings();
      setSettings(data);
      setRuntimeModeState((data.runtime_mode as RuntimeMode) ?? "safe");
    } catch (err) {
      console.error("settings_fetch_failed", err);
    } finally {
      setLoadingSettings(false);
      isInitialSettings.current = false;
    }
  }, []);

  useEffect(() => { loadSettings(); }, [loadSettings]);

  // ── Pipeline check on mount ──
  useEffect(() => {
    let active = true;
    async function checkPipeline() {
      try {
        const data = await apiFetch<PipelineBatchStatus>("/pipelines/batch/status");
        if (!active) return;
        if (data.status === "running" || data.status === "stopping") {
          setPipelineStatus(data.status === "stopping" ? "stopping" : "running");
          setPipelineProgress(data.current_lead
            ? `${data.current_lead} (${data.processed ?? 0}/${data.total ?? 0}) — ${data.current_step ?? ""}`
            : "Iniciando...");
        }
      } catch {}
    }
    checkPipeline();
    return () => { active = false; };
  }, []);

  // ── Poll pipeline ──
  const pollPipeline = useCallback(async () => {
    if (pipelineStatus !== "running") return;
    try {
      const data = await apiFetch<PipelineBatchStatus>("/pipelines/batch/status");
      if (data.status === "done") {
        setPipelineStatus("done");
        const crawlNote = data.crawl_rounds ? ` (${data.crawl_rounds} crawls, ${data.leads_from_crawl ?? 0} encontrados)` : "";
        setPipelineProgress(`${data.processed ?? 0} leads procesados${crawlNote}`);
        sileo.success({ title: `Pipeline completado: ${data.processed ?? 0} leads` });
        void Promise.all([mutateStats(), mutatePipeline(), mutateTimeSeries(), mutateIndustry(), mutateLogs()]);
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
    } catch {}
  }, [pipelineStatus, mutateStats, mutatePipeline, mutateTimeSeries, mutateIndustry, mutateLogs]);

  useVisibleInterval(pollPipeline, 2000);

  // ── Actions ──
  async function handleStartPipeline() {
    try {
      const data = await apiFetch<PipelineBatchStatus>("/pipelines/batch", { method: "POST" });
      if (data.ok) {
        setPipelineStatus("running");
        setPipelineProgress("Iniciando...");
        sileo.success({ title: "Pipeline iniciado", description: data.message });
      } else {
        sileo.error({ title: data.message ?? "Error al iniciar pipeline" });
      }
    } catch {
      sileo.error({ title: "Error de conexion al iniciar pipeline" });
    }
  }

  async function handleStopPipeline() {
    try {
      await apiFetch("/pipelines/batch/stop", { method: "POST" });
      setPipelineStatus("stopping");
      setPipelineProgress("Deteniendo...");
    } catch {
      sileo.error({ title: "Error al detener pipeline" });
    }
  }

  async function handleSetRuntimeMode(mode: RuntimeMode) {
    setSavingMode(true);
    try {
      await setRuntimeMode(mode);
      setRuntimeModeState(mode);
      sileo.success({ title: `Modo: ${mode}` });
    } catch (err) {
      sileo.error({ title: "Error al cambiar modo", description: err instanceof Error ? err.message : "" });
    } finally {
      setSavingMode(false);
    }
  }

  async function toggleFeature(key: keyof OperationalSettings, value: boolean) {
    if (!settings) return;
    setSavingKey(key);
    try {
      const updated = await updateOperationalSettings({ [key]: value });
      setSettings(updated);
      sileo.success({ title: value ? "Activado" : "Desactivado", description: [...IA_FEATURES, ...CHANNEL_FEATURES].find((f) => f.key === key)?.label });
    } catch (err) {
      sileo.error({ title: "Error al cambiar configuracion", description: err instanceof Error ? err.message : "" });
    } finally {
      setSavingKey(null);
    }
  }

  // ── Derived ──
  const healthPending = health.length === 0;
  const celeryOk = healthPending || health.find((c) => c.name === "celery")?.status === "ok";
  const ollamaOk = healthPending || health.find((c) => c.name === "ollama")?.status === "ok";
  const isRunning = pipelineStatus === "running" || pipelineStatus === "stopping";
  const loading = statsLoading;
  const error = statsError ? (statsError instanceof Error ? statsError.message : "Error desconocido") : null;

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8 space-y-6">

        {/* ═══════════════════════════════════════════════════
            COMMAND BAR — the hero element
            ═══════════════════════════════════════════════════ */}
        <div className="rounded-2xl border border-border bg-card overflow-hidden">
          <div className="grid grid-cols-1 lg:grid-cols-3 divide-y lg:divide-y-0 lg:divide-x divide-border">

            {/* Col 1: Operaciones — health + pipeline + runtime + low resources */}
            <div className="p-4 flex flex-col gap-4">
              {/* Health */}
              <div className="flex flex-col gap-2 flex-1">
                <div className="flex items-center justify-between">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Sistema</p>
                  <button
                    onClick={() => { refreshHealth(); loadSettings(); }}
                    className="rounded-lg p-1 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                    title="Actualizar estado"
                  >
                    <RefreshCw className={cn("h-3 w-3", healthLoading && "animate-spin")} />
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-1.5 flex-1">
                  {(() => {
                    const HEALTH_META: Record<string, { label: string; icon: React.ElementType; desc: string }> = {
                      database: { label: "BD", icon: Database, desc: "PostgreSQL" },
                      redis: { label: "Redis", icon: HardDrive, desc: "Cache & broker" },
                      ollama: { label: "Ollama", icon: Brain, desc: "Modelos IA" },
                      celery: { label: "Celery", icon: Zap, desc: "Workers async" },
                    };
                    const items = health.length > 0
                      ? health.map((c) => ({ ...c, meta: HEALTH_META[c.name] }))
                      : Object.entries(HEALTH_META).map(([name, meta]) => ({ name, status: "pending" as const, latency_ms: null, error: null, meta }));

                    return items.map((c) => {
                      const Icon = c.meta?.icon ?? Brain;
                      const isPending = c.status === "pending";
                      return (
                        <div
                          key={c.name}
                          className={cn(
                            "flex items-center gap-2.5 rounded-lg border px-3 py-2.5 transition-colors",
                            isPending
                              ? "border-border/40 bg-muted/20"
                              : c.status === "ok"
                              ? "border-emerald-200 dark:border-emerald-900/30 bg-emerald-50/50 dark:bg-emerald-950/10"
                              : c.status === "degraded"
                              ? "border-amber-200 dark:border-amber-900/30 bg-amber-50/50 dark:bg-amber-950/10"
                              : "border-red-200 dark:border-red-900/30 bg-red-50/50 dark:bg-red-950/10"
                          )}
                          title={c.error || (c.latency_ms ? `${c.latency_ms.toFixed(0)}ms` : "")}
                        >
                          <Icon className={cn("h-4 w-4 shrink-0", isPending ? "text-muted-foreground/30" : "text-muted-foreground")} />
                          <div className="flex-1 min-w-0">
                            <p className={cn("text-xs font-semibold", isPending ? "text-muted-foreground/40" : "text-foreground")}>
                              {c.meta?.label ?? c.name}
                            </p>
                            <p className="text-[10px] text-muted-foreground truncate">
                              {isPending ? c.meta?.desc : c.latency_ms != null
                                ? `${c.meta?.desc} · ${c.latency_ms < 1000 ? `${c.latency_ms.toFixed(0)}ms` : `${(c.latency_ms / 1000).toFixed(1)}s`}`
                                : c.meta?.desc}
                            </p>
                          </div>
                          {!isPending && (
                            <span className={cn(
                              "h-2 w-2 rounded-full shrink-0",
                              c.status === "ok" ? "bg-emerald-500" : c.status === "degraded" ? "bg-amber-500" : "bg-red-500"
                            )} />
                          )}
                        </div>
                      );
                    });
                  })()}
                </div>
              </div>

              {/* Runtime mode + Pipeline — pushed to bottom */}
              <div className="space-y-3 mt-auto">
                <div className="space-y-2">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Modo Runtime</p>
                  <div className="flex gap-1">
                    {(["safe", "assisted", "auto"] as const).map((mode) => (
                      <button
                        key={mode}
                        onClick={() => void handleSetRuntimeMode(mode)}
                        disabled={savingMode}
                        title={mode === "safe" ? "Maxima seguridad" : mode === "assisted" ? "Pipeline automatico" : "Full auto"}
                        className={cn(
                          "flex-1 rounded-lg py-2 text-xs font-bold uppercase tracking-wider transition-all",
                          runtimeMode === mode
                            ? mode === "safe" ? "bg-emerald-600 text-white"
                              : mode === "assisted" ? "bg-amber-500 text-white"
                              : "bg-red-600 text-white"
                            : "bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground"
                        )}
                      >
                        {mode === "safe" ? "Safe" : mode === "assisted" ? "Assist" : "Auto"}
                      </button>
                    ))}
                  </div>
                  {savingMode && (
                    <div className="flex items-center gap-1.5">
                      <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
                      <span className="text-[10px] text-muted-foreground">Guardando...</span>
                    </div>
                  )}
                </div>

                {/* Pipeline */}
                <div className="space-y-2">
                  {!isRunning ? (
                    <Button
                      onClick={handleStartPipeline}
                      disabled={!celeryOk}
                      size="lg"
                      className="w-full rounded-xl"
                    >
                      <Play className="h-4 w-4" />
                      Iniciar Pipeline
                    </Button>
                  ) : (
                    <Button
                      variant="destructive-solid"
                      onClick={handleStopPipeline}
                      disabled={pipelineStatus === "stopping"}
                      size="lg"
                      className="w-full rounded-xl"
                    >
                      <Square className="h-3.5 w-3.5" />
                      {pipelineStatus === "stopping" ? "Deteniendo..." : "Detener"}
                    </Button>
                  )}
                  {pipelineProgress && (
                    <div className="flex items-center gap-2">
                      {isRunning && <Loader2 className="h-3 w-3 animate-spin text-muted-foreground shrink-0" />}
                      <span className={cn(
                        "text-[10px] font-medium truncate font-data",
                        pipelineStatus === "done" ? "text-emerald-600 dark:text-emerald-400" : "text-muted-foreground"
                      )}>
                        {pipelineProgress}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Col 2: Inteligencia Artificial */}
            <div className="p-4 space-y-2">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                IA & Agentes
              </p>
              <FeatureToggleList
                features={IA_FEATURES}
                settings={settings}
                loading={loadingSettings}
                savingKey={savingKey}
                accentColor="emerald"
                onToggle={toggleFeature}
                warningMessage={!ollamaOk ? "Ollama no esta corriendo — los features de IA no van a funcionar" : undefined}
              />
            </div>

            {/* Col 3: Canales */}
            <div className="p-4 space-y-2">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                Canales de salida
              </p>
              <FeatureToggleList
                features={CHANNEL_FEATURES}
                settings={settings}
                loading={loadingSettings}
                savingKey={savingKey}
                accentColor="emerald"
                onToggle={toggleFeature}
              />
            </div>
          </div>
        </div>

        {/* ═══════════════════════════════════════════════════
            ERROR STATE
            ═══════════════════════════════════════════════════ */}
        {error && !loading && (
          <div className="rounded-2xl border border-destructive/40 bg-destructive/10 p-6 text-center space-y-3">
            <p className="text-sm font-medium text-destructive">No se pudo cargar el panel</p>
            <p className="text-xs text-muted-foreground">{error}</p>
            <button
              onClick={() => void Promise.all([mutateStats(), mutatePipeline(), mutateTimeSeries(), mutateIndustry(), mutateLogs()])}
              className="inline-flex items-center rounded-xl bg-foreground px-4 py-2 text-sm font-medium text-background hover:bg-foreground/80 transition-colors"
            >
              Reintentar
            </button>
          </div>
        )}

        {/* ═══════════════════════════════════════════════════
            KEY METRICS
            ═══════════════════════════════════════════════════ */}
        {loading ? (
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => <SkeletonStatCard key={i} />)}
          </div>
        ) : stats ? (
          <StatsGrid stats={stats} />
        ) : null}

        {/* ═══════════════════════════════════════════════════
            CHARTS & DATA
            ═══════════════════════════════════════════════════ */}
        {loading ? (
          <div className="grid gap-6 lg:grid-cols-2">
            {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} className="h-[280px]" />)}
          </div>
        ) : (
          <>
            <div className="grid gap-6 lg:grid-cols-2">
              <PipelineFunnel stages={pipeline ?? []} />
              <IndustryChart data={industryBreakdown ?? []} />
            </div>

            <div className="grid gap-6 lg:grid-cols-3">
              <AreaChartCard
                title="Leads por Dia"
                subtitle="Ultimos 30 dias"
                data={timeSeries ?? []}
                dataKey="leads"
                color="oklch(0.45 0 0)"
                gradientId="leadsGrad"
              />
              <AreaChartCard
                title="Outreach por Dia"
                subtitle="Emails enviados"
                data={timeSeries ?? []}
                dataKey="outreach"
                color="oklch(0.55 0 0)"
                gradientId="outreachGrad"
              />
              <AreaChartCard
                title="Respuestas por Dia"
                subtitle="Replies recibidos"
                data={timeSeries ?? []}
                dataKey="replies"
                color="oklch(0.35 0 0)"
                gradientId="repliesGrad"
              />
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
              <RecentActivity logs={logs ?? []} />
              <TerritorySummary />
            </div>
          </>
        )}
      </div>
    </div>
  );
}

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useVisibleInterval } from "@/lib/hooks/use-visible-interval";
import {
  Brain,
  Mail,
  MessageCircle,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { sileo } from "sileo";
import {
  getOperationalSettings,
  updateOperationalSettings,
  setRuntimeMode,
  getTerritories,
  apiFetch,
} from "@/lib/api/client";
import type { HealthComponent, OperationalSettings, RuntimeMode, TerritoryWithStats } from "@/types";

import { HealthStatus } from "./health-status";
import { RuntimeModePanel } from "./runtime-mode-panel";
import { PipelineControls } from "./pipeline-controls";
import { CrawlControls } from "./crawl-controls";
import { FeatureToggleList, type FeatureToggle } from "./feature-toggle-list";

// ─── Types ──────────────────────────────────────────────────────────────────

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

interface CrawlTerritoryStatus {
  status: string;
  ok?: boolean;
  message?: string;
  task_id?: string;
  current_city?: string | null;
  current_city_idx?: number;
  total_cities?: number;
  leads_created?: number;
  error?: string;
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
    key: "whatsapp_outreach_enabled",
    label: "WhatsApp outreach",
    hint: "Genera drafts de WhatsApp en el pipeline",
    icon: MessageCircle,
    category: "whatsapp",
  },
  {
    key: "whatsapp_agent_enabled",
    label: "Agente WhatsApp",
    hint: "Mote responde mensajes por WhatsApp",
    icon: Brain,
    category: "whatsapp",
  },
];

const IA_FEATURES = FEATURES.filter((f) => f.category === "ia");
const CHANNEL_FEATURES = FEATURES.filter((f) => f.category === "mail" || f.category === "whatsapp");

const LS_CRAWL_TERRITORY_KEY = "cs:crawl_territory_id";

// ─── Component ──────────────────────────────────────────────────────────────

interface ControlCenterProps {
  health: HealthComponent[];
  healthLoading?: boolean;
  onRefreshHealth?: () => void;
}

export function ControlCenter({ health, healthLoading, onRefreshHealth }: ControlCenterProps) {
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
  const [runtimeMode, setRuntimeModeState] = useState<RuntimeMode>("safe");
  const [savingMode, setSavingMode] = useState(false);

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

  // Check batch pipeline status on mount + poll when running
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
        } else if (data.status === "done") {
          setPipelineStatus("done");
          setPipelineProgress(`Listo — ${data.processed ?? 0} leads procesados`);
        }
      } catch (err) { console.error("pipeline_status_check_failed", err); }
    }
    checkPipeline();
    return () => { active = false; };
  }, []);

  const pollPipelineStatus = useCallback(async () => {
    if (pipelineStatus !== "running") return;
    try {
      const data = await apiFetch<PipelineBatchStatus>("/pipelines/batch/status");
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
    } catch (err) { console.error("pipeline_status_poll_failed", err); }
  }, [pipelineStatus]);

  useVisibleInterval(pollPipelineStatus, 2000);

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
          apiFetch<CrawlTerritoryStatus>(`/crawl/territory/${tid}/status`)
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
  const pollCrawlStatus = useCallback(async () => {
    if (crawlStatus !== "running" || !selectedTerritoryId) return;
    try {
      const data = await apiFetch<CrawlTerritoryStatus>(`/crawl/territory/${selectedTerritoryId}/status`);
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
    } catch (err) { console.error("crawl_status_poll_failed", err); }
  }, [crawlStatus, selectedTerritoryId]);

  useVisibleInterval(pollCrawlStatus, 2000);

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
      const data = await apiFetch<PipelineBatchStatus>("/pipelines/batch", { method: "POST" });
      if (data.ok) {
        setPipelineStatus("running");
        setPipelineProgress("Iniciando...");
        sileo.success({ title: "Pipeline iniciado", description: data.message });
      } else {
        sileo.error({ title: data.message ?? "Error al iniciar pipeline" });
      }
    } catch (err) {
      console.error("pipeline_run_start_failed", err);
      sileo.error({ title: "Error de conexion al iniciar pipeline" });
    }
  }

  async function handleStopPipeline() {
    try {
      await apiFetch("/pipelines/batch/stop", { method: "POST" });
      setPipelineStatus("stopping");
      setPipelineProgress("Deteniendo...");
    } catch (err) {
      console.error("pipeline_run_stop_failed", err);
      sileo.error({ title: "Error al detener pipeline" });
    }
  }

  async function handleStartCrawl() {
    if (!selectedTerritoryId) return;
    try {
      const data = await apiFetch<CrawlTerritoryStatus>("/crawl/territory", {
        method: "POST",
        body: JSON.stringify({ territory_id: selectedTerritoryId }),
      });
      if (data.ok) {
        setCrawlStatus("running");
        setCrawlProgress("Iniciando...");
        setCrawlTaskId(data.task_id ?? null);
        localStorage.setItem(LS_CRAWL_TERRITORY_KEY, selectedTerritoryId);
        sileo.success({ title: "Crawl iniciado", description: data.message });
      } else {
        sileo.error({ title: data.message ?? "Error al iniciar crawl" });
      }
    } catch (err) {
      console.error("crawl_start_failed", err);
      sileo.error({ title: "Error de conexion al iniciar crawl" });
    }
  }

  async function handleStopCrawl() {
    if (!selectedTerritoryId) return;
    try {
      if (crawlTaskId) {
        await apiFetch(`/tasks/${crawlTaskId}/revoke`, { method: "POST" });
      }
      await apiFetch(`/crawl/territory/${selectedTerritoryId}/stop`, { method: "POST" });
      setCrawlStatus("idle");
      setCrawlProgress(null);
      setCrawlTaskId(null);
      localStorage.removeItem(LS_CRAWL_TERRITORY_KEY);
      sileo.success({ title: "Crawl detenido" });
    } catch (err) {
      console.error("crawl_stop_failed", err);
      sileo.error({ title: "Error al detener crawl" });
    }
  }

  async function handleSetRuntimeMode(mode: RuntimeMode) {
    setSavingMode(true);
    try {
      await setRuntimeMode(mode);
      setRuntimeModeState(mode);
      sileo.success({ title: `Modo: ${mode}` });
    } catch (err) {
      sileo.error({
        title: "Error al cambiar modo",
        description: err instanceof Error ? err.message : "Error desconocido",
      });
    } finally {
      setSavingMode(false);
    }
  }

  function handleTerritoryChange(id: string) {
    setSelectedTerritoryId(id);
    setCrawlStatus("idle");
    setCrawlProgress(null);
  }

  const ollamaOk = health.find((c) => c.name === "ollama")?.status === "ok";
  const celeryOk = health.find((c) => c.name === "celery")?.status === "ok";

  return (
    <div className="rounded-2xl border border-border bg-card overflow-hidden">
      <HealthStatus
        health={health}
        healthLoading={healthLoading}
        onRefresh={() => { onRefreshHealth?.(); loadSettings(); }}
      />

      <RuntimeModePanel
        currentMode={runtimeMode}
        saving={savingMode}
        onChange={(mode) => void handleSetRuntimeMode(mode)}
      />

      <div className="grid gap-0 lg:grid-cols-3">
        {/* Col 1: Operations */}
        <div className="border-b lg:border-b-0 lg:border-r border-border p-4 space-y-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Operaciones
          </p>
          <PipelineControls
            pipelineStatus={pipelineStatus}
            pipelineProgress={pipelineProgress}
            celeryOk={celeryOk ?? false}
            onStart={handleRunPipeline}
            onStop={handleStopPipeline}
          />
          <CrawlControls
            crawlStatus={crawlStatus}
            crawlProgress={crawlProgress}
            territories={territories}
            selectedTerritoryId={selectedTerritoryId}
            celeryOk={celeryOk ?? false}
            onTerritoryChange={handleTerritoryChange}
            onStart={handleStartCrawl}
            onStop={handleStopCrawl}
          />
        </div>

        {/* Col 2: IA Features */}
        <div className="border-b lg:border-b-0 lg:border-r border-border p-4 space-y-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Inteligencia Artificial
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

        {/* Col 3: Channels */}
        <div className="p-4 space-y-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Canales
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
  );
}

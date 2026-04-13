"use client";

import { useCallback } from "react";
import { useSystemHealth } from "@/lib/hooks/use-system-health";
import { useApi } from "@/lib/hooks/use-swr-fetch";
import { StatsGrid } from "@/components/dashboard/stats-grid";
import { PipelineFunnel } from "@/components/dashboard/pipeline-funnel";
import { AreaChartCard } from "@/components/charts/area-chart-card";
import { IndustryChart } from "@/components/dashboard/industry-chart";
import { RecentActivity } from "@/components/dashboard/recent-activity";
import { TerritorySummary } from "@/components/dashboard/territory-summary";
import { HealthGrid } from "@/components/dashboard/health-grid";
import { PipelineControls } from "@/components/dashboard/pipeline-controls";
import { RuntimeModeSelector } from "@/components/dashboard/runtime-mode-selector";
import { FeatureToggles } from "@/components/dashboard/feature-toggles";
import { SkeletonStatCard, SkeletonCard } from "@/components/shared/skeleton";
import { usePipeline } from "./use-pipeline";
import { useSettings } from "./use-settings";
import { IA_FEATURES, CHANNEL_FEATURES } from "./feature-defs";
import type {
  DashboardStats,
  IndustryBreakdown,
  OutreachLog,
  PipelineStage,
  TimeSeriesPoint,
} from "@/types";

export default function PanelPage() {
  // Health
  const { components: health, loading: healthLoading, refresh: refreshHealth } = useSystemHealth();

  // Dashboard data
  const { data: stats, isLoading: statsLoading, error: statsError, mutate: mutateStats } = useApi<DashboardStats>("/dashboard/stats");
  const { data: pipeline, mutate: mutatePipeline } = useApi<PipelineStage[]>("/dashboard/pipeline");
  const { data: timeSeries, mutate: mutateTimeSeries } = useApi<TimeSeriesPoint[]>("/dashboard/time-series?days=30");
  const { data: industryBreakdown, mutate: mutateIndustry } = useApi<IndustryBreakdown[]>("/performance/industry");
  const { data: logs, mutate: mutateLogs } = useApi<OutreachLog[]>("/outreach/logs?limit=8");

  const refreshAll = useCallback(
    () => void Promise.all([mutateStats(), mutatePipeline(), mutateTimeSeries(), mutateIndustry(), mutateLogs()]),
    [mutateStats, mutatePipeline, mutateTimeSeries, mutateIndustry, mutateLogs],
  );

  // Pipeline
  const { pipelineStatus, pipelineProgress, handleStart, handleStop } = usePipeline(refreshAll);

  // Settings & runtime
  const {
    settings, savingKey, runtimeMode, savingMode, loadingSettings,
    loadSettings, handleSetRuntimeMode, toggleFeature,
  } = useSettings();

  // Derived
  const healthPending = health.length === 0;
  const celeryOk = healthPending || health.find((c) => c.name === "celery")?.status === "ok";
  const ollamaOk = healthPending || health.find((c) => c.name === "ollama")?.status === "ok";
  const loading = statsLoading;
  const error = statsError ? (statsError instanceof Error ? statsError.message : "Error desconocido") : null;

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8 space-y-6">

        {/* ═══ COMMAND BAR ═══ */}
        <div className="rounded-2xl border border-border bg-card overflow-hidden">
          <div className="grid grid-cols-1 lg:grid-cols-3 divide-y lg:divide-y-0 lg:divide-x divide-border">

            {/* Col 1: Operaciones */}
            <div className="p-4 flex flex-col gap-4">
              <HealthGrid
                health={health}
                healthLoading={healthLoading}
                onRefresh={() => { refreshHealth(); loadSettings(); }}
              />
              <div className="space-y-3 mt-auto">
                <RuntimeModeSelector
                  currentMode={runtimeMode}
                  saving={savingMode}
                  onChange={handleSetRuntimeMode}
                />
                <PipelineControls
                  pipelineStatus={pipelineStatus}
                  pipelineProgress={pipelineProgress}
                  celeryOk={Boolean(celeryOk)}
                  onStart={handleStart}
                  onStop={handleStop}
                />
              </div>
            </div>

            {/* Col 2: IA & Agentes */}
            <FeatureToggles
              title="IA & Agentes"
              features={IA_FEATURES}
              settings={settings}
              loading={loadingSettings}
              savingKey={savingKey}
              onToggle={toggleFeature}
              warningMessage={!ollamaOk ? "Ollama no esta corriendo — los features de IA no van a funcionar" : undefined}
            />

            {/* Col 3: Canales */}
            <FeatureToggles
              title="Canales de salida"
              features={CHANNEL_FEATURES}
              settings={settings}
              loading={loadingSettings}
              savingKey={savingKey}
              onToggle={toggleFeature}
            />
          </div>
        </div>

        {/* ═══ ERROR STATE ═══ */}
        {error && !loading && (
          <div className="rounded-2xl border border-destructive/40 bg-destructive/10 p-6 text-center space-y-3">
            <p className="text-sm font-medium text-destructive">No se pudo cargar el panel</p>
            <p className="text-xs text-muted-foreground">{error}</p>
            <button
              onClick={refreshAll}
              className="inline-flex items-center rounded-xl bg-foreground px-4 py-2 text-sm font-medium text-background hover:bg-foreground/80 transition-colors"
            >
              Reintentar
            </button>
          </div>
        )}

        {/* ═══ KEY METRICS ═══ */}
        {loading ? (
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => <SkeletonStatCard key={i} />)}
          </div>
        ) : stats ? (
          <StatsGrid stats={stats} />
        ) : null}

        {/* ═══ CHARTS & DATA ═══ */}
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

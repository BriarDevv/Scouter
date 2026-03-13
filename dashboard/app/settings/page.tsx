"use client";

import { useEffect, useState } from "react";
import { Bot, BrainCircuit, Cpu, Lock, RefreshCw, Settings, ShieldCheck, TriangleAlert } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { getLLMSettings } from "@/lib/api/client";
import type { LLMSettings } from "@/types";

function SectionCard({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-5">
        <h2 className="font-heading text-base font-semibold text-slate-900">{title}</h2>
        {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
      </div>
      {children}
    </section>
  );
}

function ModelRow({
  label,
  model,
  icon: Icon,
}: {
  label: string;
  model: string | null;
  icon: typeof Bot;
}) {
  return (
    <div className="flex items-center justify-between rounded-2xl border border-slate-100 bg-slate-50/70 px-4 py-3">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-900 text-white">
          <Icon className="h-4 w-4" />
        </div>
        <div>
          <p className="text-sm font-medium text-slate-900">{label}</p>
          <p className="text-xs text-slate-500">Configuración activa por rol</p>
        </div>
      </div>
      <code className="rounded-lg bg-white px-3 py-1.5 text-sm text-slate-700 shadow-sm">
        {model ?? "No configurado"}
      </code>
    </div>
  );
}

function MetaRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-slate-100 py-3 last:border-b-0">
      <span className="text-sm text-slate-500">{label}</span>
      <div className="text-right text-sm font-medium text-slate-900">{value}</div>
    </div>
  );
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<LLMSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadSettings() {
      setLoading(true);
      setError(null);

      try {
        const nextSettings = await getLLMSettings();
        if (!active) {
          return;
        }
        setSettings(nextSettings);
      } catch (err) {
        if (!active) {
          return;
        }
        setError(err instanceof Error ? err.message : "No se pudo cargar la configuración LLM.");
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadSettings();

    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Configuración"
        description="Estado real de la configuración LLM por rol. La edición desde UI queda pendiente."
      />

      {loading && (
        <div className="grid gap-6 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="animate-pulse space-y-4">
                <div className="h-4 w-40 rounded bg-slate-200" />
                <div className="h-10 rounded-xl bg-slate-100" />
                <div className="h-10 rounded-xl bg-slate-100" />
                <div className="h-10 rounded-xl bg-slate-100" />
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && error && (
        <SectionCard
          title="No se pudo cargar Settings"
          description="La pantalla es real y depende del backend. No usa mocks ni valores inventados."
        >
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-4 text-sm text-rose-700">
            <div className="flex items-start gap-3">
              <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" />
              <div>
                <p className="font-medium">Error al consultar `/api/v1/settings/llm`</p>
                <p className="mt-1 text-rose-600">{error}</p>
              </div>
            </div>
          </div>
        </SectionCard>
      )}

      {!loading && !error && !settings && (
        <EmptyState
          icon={Settings}
          title="Sin configuración disponible"
          description="El backend respondió sin datos para la configuración LLM."
        />
      )}

      {!loading && !error && settings && (
        <div className="grid gap-6 lg:grid-cols-[1.2fr,0.8fr]">
          <div className="space-y-6">
            <SectionCard
              title="Configuración de modelos"
              description="Modelos activos por rol dentro del sistema actual."
            >
              <div className="space-y-3">
                <ModelRow label="Leader Model" model={settings.leader_model} icon={BrainCircuit} />
                <ModelRow label="Executor Model" model={settings.executor_model} icon={Cpu} />
                <ModelRow label="Reviewer Model" model={settings.reviewer_model} icon={ShieldCheck} />
              </div>
            </SectionCard>

            <SectionCard
              title="Catálogo soportado"
              description="Modelos permitidos actualmente por la configuración central."
            >
              <div className="flex flex-wrap gap-2">
                {settings.supported_models.map((model) => (
                  <code
                    key={model}
                    className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700"
                  >
                    {model}
                  </code>
                ))}
              </div>
            </SectionCard>
          </div>

          <div className="space-y-6">
            <SectionCard
              title="Compatibilidad actual"
              description="Detalles de provider y fallback legacy del executor."
            >
              <MetaRow label="Provider" value={settings.provider} />
              <MetaRow label="Base URL" value={<code>{settings.base_url}</code>} />
              <MetaRow
                label="Legacy executor fallback"
                value={
                  <div className="space-y-1">
                    <div>
                      <code>{settings.legacy_executor_fallback_model}</code>
                    </div>
                    <p className="text-xs font-normal text-slate-500">
                      {settings.legacy_executor_fallback_active
                        ? "Activo porque no hay override explícito de OLLAMA_EXECUTOR_MODEL."
                        : "Disponible solo como compatibilidad legacy; hoy no es el modelo activo del executor."}
                    </p>
                  </div>
                }
              />
              <MetaRow label="Timeout" value={`${settings.timeout_seconds}s`} />
              <MetaRow label="Reintentos" value={settings.max_retries} />
            </SectionCard>

            <SectionCard
              title="Estado del modo actual"
              description="La edición desde UI todavía no está habilitada para evitar settings falsos o inconsistentes."
            >
              <div className="space-y-4">
                <div className="flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-4">
                  <Lock className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
                  <div>
                    <p className="text-sm font-medium text-amber-900">Read-only real</p>
                    <p className="mt-1 text-sm text-amber-800">
                      Esta pantalla refleja la configuración efectiva del backend. La edición en caliente queda
                      pendiente para una fase posterior.
                    </p>
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-100 bg-slate-50/70 px-4 py-4">
                  <div className="flex items-center gap-2 text-sm font-medium text-slate-900">
                    <RefreshCw className="h-4 w-4" />
                    Defaults preparados
                  </div>
                  <div className="mt-3 space-y-2 text-sm text-slate-600">
                    <div className="flex items-center justify-between">
                      <span>Leader</span>
                      <code>{settings.default_role_models.leader}</code>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Executor</span>
                      <code>{settings.default_role_models.executor}</code>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Reviewer</span>
                      <code>{settings.default_role_models.reviewer ?? "No definido"}</code>
                    </div>
                  </div>
                </div>
              </div>
            </SectionCard>
          </div>
        </div>
      )}
    </div>
  );
}

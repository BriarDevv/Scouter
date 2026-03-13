"use client";

import { useEffect, useState } from "react";
import {
  Bot,
  BrainCircuit,
  Cpu,
  Lock,
  Mail,
  RefreshCw,
  Settings,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { RelativeTime } from "@/components/shared/relative-time";
import { getLLMSettings, getMailSettings } from "@/lib/api/client";
import type { LLMSettings, MailSettings } from "@/types";

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

function StatusPill({
  label,
  tone,
}: {
  label: string;
  tone: "positive" | "warning" | "neutral" | "danger";
}) {
  const styles = {
    positive: "bg-emerald-50 text-emerald-700",
    warning: "bg-amber-50 text-amber-700",
    neutral: "bg-slate-100 text-slate-600",
    danger: "bg-rose-50 text-rose-700",
  };

  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${styles[tone]}`}>
      {label}
    </span>
  );
}

function MissingRequirements({ items }: { items: string[] }) {
  if (items.length === 0) {
    return (
      <p className="text-xs text-slate-500">
        No faltan requisitos no sensibles visibles desde la app.
      </p>
    );
  }

  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <code
          key={item}
          className="rounded-lg border border-rose-200 bg-rose-50 px-2.5 py-1 text-xs text-rose-700"
        >
          {item}
        </code>
      ))}
    </div>
  );
}

export default function SettingsPage() {
  const [llmSettings, setLlmSettings] = useState<LLMSettings | null>(null);
  const [mailSettings, setMailSettings] = useState<MailSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [llmError, setLlmError] = useState<string | null>(null);
  const [mailError, setMailError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadSettings() {
      setLoading(true);
      setLlmError(null);
      setMailError(null);

      const [llmResult, mailResult] = await Promise.allSettled([
        getLLMSettings(),
        getMailSettings(),
      ]);

      if (!active) {
        return;
      }

      if (llmResult.status === "fulfilled") {
        setLlmSettings(llmResult.value);
      } else {
        setLlmSettings(null);
        setLlmError(
          llmResult.reason instanceof Error
            ? llmResult.reason.message
            : "No se pudo cargar la configuración LLM."
        );
      }

      if (mailResult.status === "fulfilled") {
        setMailSettings(mailResult.value);
      } else {
        setMailSettings(null);
        setMailError(
          mailResult.reason instanceof Error
            ? mailResult.reason.message
            : "No se pudo cargar la configuración de mail."
        );
      }

      setLoading(false);
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
        description="Estado real de modelos y canal mail. La edición desde UI sigue deshabilitada para no vender humo ni exponer secretos."
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

      {!loading && !llmSettings && !mailSettings && (
        <EmptyState
          icon={Settings}
          title="Sin configuración disponible"
          description="El backend no pudo devolver ni la configuración LLM ni la de mail."
        />
      )}

      {!loading && (llmError || mailError) && (
        <div className="grid gap-4 lg:grid-cols-2">
          {llmError && (
            <SectionCard
              title="No se pudo cargar LLM Settings"
              description="La pantalla usa datos reales del backend y no cae a mocks."
            >
              <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-4 text-sm text-rose-700">
                <div className="flex items-start gap-3">
                  <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" />
                  <div>
                    <p className="font-medium">Error al consultar `/api/v1/settings/llm`</p>
                    <p className="mt-1 text-rose-600">{llmError}</p>
                  </div>
                </div>
              </div>
            </SectionCard>
          )}

          {mailError && (
            <SectionCard
              title="No se pudo cargar Mail Settings"
              description="El canal mail se muestra desde la configuración efectiva y el último sync persistido."
            >
              <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-4 text-sm text-rose-700">
                <div className="flex items-start gap-3">
                  <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" />
                  <div>
                    <p className="font-medium">Error al consultar `/api/v1/settings/mail`</p>
                    <p className="mt-1 text-rose-600">{mailError}</p>
                  </div>
                </div>
              </div>
            </SectionCard>
          )}
        </div>
      )}

      {llmSettings && (
        <div className="grid gap-6 lg:grid-cols-[1.2fr,0.8fr]">
          <div className="space-y-6">
            <SectionCard
              title="Configuración de modelos"
              description="Modelos activos por rol dentro del sistema actual."
            >
              <div className="space-y-3">
                <ModelRow label="Leader Model" model={llmSettings.leader_model} icon={BrainCircuit} />
                <ModelRow label="Executor Model" model={llmSettings.executor_model} icon={Cpu} />
                <ModelRow label="Reviewer Model" model={llmSettings.reviewer_model} icon={ShieldCheck} />
              </div>
            </SectionCard>

            <SectionCard
              title="Catálogo soportado"
              description="Modelos permitidos actualmente por la configuración central."
            >
              <div className="flex flex-wrap gap-2">
                {llmSettings.supported_models.map((model) => (
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
              <MetaRow label="Provider" value={llmSettings.provider} />
              <MetaRow label="Base URL" value={<code>{llmSettings.base_url}</code>} />
              <MetaRow
                label="Legacy executor fallback"
                value={
                  <div className="space-y-1">
                    <div>
                      <code>{llmSettings.legacy_executor_fallback_model}</code>
                    </div>
                    <p className="text-xs font-normal text-slate-500">
                      {llmSettings.legacy_executor_fallback_active
                        ? "Activo porque no hay override explícito de OLLAMA_EXECUTOR_MODEL."
                        : "Disponible solo como compatibilidad legacy; hoy no es el modelo activo del executor."}
                    </p>
                  </div>
                }
              />
              <MetaRow label="Timeout" value={`${llmSettings.timeout_seconds}s`} />
              <MetaRow label="Reintentos" value={llmSettings.max_retries} />
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
                      Esta sección refleja la configuración efectiva del backend. La edición en caliente queda
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
                      <code>{llmSettings.default_role_models.leader}</code>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Executor</span>
                      <code>{llmSettings.default_role_models.executor}</code>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Reviewer</span>
                      <code>{llmSettings.default_role_models.reviewer ?? "No definido"}</code>
                    </div>
                  </div>
                </div>
              </div>
            </SectionCard>
          </div>
        </div>
      )}

      {mailSettings && (
        <div className="grid gap-6 lg:grid-cols-[1.2fr,0.8fr]">
          <div className="space-y-6">
            <SectionCard
              title="Mail outbound"
              description="Configuración operativa no sensible del canal de envío real."
            >
              <div className="mb-4 flex flex-wrap gap-2">
                <StatusPill
                  label={mailSettings.outbound.enabled ? "Outbound enabled" : "Outbound disabled"}
                  tone={mailSettings.outbound.enabled ? "positive" : "neutral"}
                />
                <StatusPill
                  label={mailSettings.outbound.configured ? "Configurado" : "Incompleto"}
                  tone={mailSettings.outbound.configured ? "positive" : "warning"}
                />
                <StatusPill
                  label={mailSettings.outbound.ready ? "Ready" : "No listo"}
                  tone={mailSettings.outbound.ready ? "positive" : "warning"}
                />
              </div>
              <MetaRow label="Provider" value={mailSettings.outbound.provider} />
              <MetaRow label="From email" value={mailSettings.outbound.from_email ?? "No configurado"} />
              <MetaRow label="From name" value={mailSettings.outbound.from_name} />
              <MetaRow label="Reply-To" value={mailSettings.outbound.reply_to ?? "No configurado"} />
              <MetaRow label="Send timeout" value={`${mailSettings.outbound.send_timeout_seconds}s`} />
              <MetaRow
                label="Envío seguro"
                value={mailSettings.outbound.require_approved_drafts ? "Solo drafts approved" : "Sin restricción"}
              />
              <div className="mt-4 rounded-2xl border border-slate-100 bg-slate-50/70 px-4 py-4">
                <p className="text-sm font-medium text-slate-900">Faltantes no sensibles</p>
                <p className="mt-1 text-xs text-slate-500">
                  La app no expone secretos. Solo muestra qué piezas faltan para dejar el canal listo.
                </p>
                <div className="mt-3">
                  <MissingRequirements items={mailSettings.outbound.missing_requirements} />
                </div>
              </div>
            </SectionCard>

            <SectionCard
              title="Mail inbound"
              description="Configuración operativa del canal de lectura/sync del inbox comercial."
            >
              <div className="mb-4 flex flex-wrap gap-2">
                <StatusPill
                  label={mailSettings.inbound.enabled ? "Inbound enabled" : "Inbound disabled"}
                  tone={mailSettings.inbound.enabled ? "positive" : "neutral"}
                />
                <StatusPill
                  label={mailSettings.inbound.configured ? "Configurado" : "Incompleto"}
                  tone={mailSettings.inbound.configured ? "positive" : "warning"}
                />
                <StatusPill
                  label={mailSettings.inbound.ready ? "Ready" : "No listo"}
                  tone={mailSettings.inbound.ready ? "positive" : "warning"}
                />
              </div>
              <MetaRow label="Provider" value={mailSettings.inbound.provider} />
              <MetaRow label="Cuenta de lectura" value={mailSettings.inbound.account ?? "No configurada"} />
              <MetaRow label="Mailbox" value={mailSettings.inbound.mailbox} />
              <MetaRow label="Sync limit" value={mailSettings.inbound.sync_limit} />
              <MetaRow label="Timeout" value={`${mailSettings.inbound.timeout_seconds}s`} />
              <MetaRow label="Search criteria" value={<code>{mailSettings.inbound.search_criteria || "ALL"}</code>} />
              <MetaRow
                label="Auto classify inbound"
                value={mailSettings.inbound.auto_classify_inbound ? "Activo" : "Desactivado"}
              />
              <MetaRow
                label="Reviewer para labels"
                value={
                  mailSettings.inbound.use_reviewer_for_labels.length > 0
                    ? mailSettings.inbound.use_reviewer_for_labels.join(", ")
                    : "Sin reglas configuradas"
                }
              />
              <div className="mt-4 rounded-2xl border border-slate-100 bg-slate-50/70 px-4 py-4">
                <p className="text-sm font-medium text-slate-900">Faltantes no sensibles</p>
                <p className="mt-1 text-xs text-slate-500">
                  Las credenciales IMAP permanecen fuera de la UI; solo se informa si falta alguna pieza crítica.
                </p>
                <div className="mt-3">
                  <MissingRequirements items={mailSettings.inbound.missing_requirements} />
                </div>
              </div>
            </SectionCard>
          </div>

          <div className="space-y-6">
            <SectionCard
              title="Estado del canal mail"
              description="Read-only real sobre readiness, última sync y separación entre config visible y secretos."
            >
              <div className="mb-4 flex flex-wrap gap-2">
                <StatusPill
                  label={mailSettings.health.enabled ? "Algún canal habilitado" : "Canales deshabilitados"}
                  tone={mailSettings.health.enabled ? "positive" : "neutral"}
                />
                <StatusPill
                  label={mailSettings.health.configured ? "Hay configuración base" : "Configuración incompleta"}
                  tone={mailSettings.health.configured ? "positive" : "warning"}
                />
              </div>
              <MetaRow
                label="Outbound ready"
                value={<StatusPill label={mailSettings.health.outbound_ready ? "Sí" : "No"} tone={mailSettings.health.outbound_ready ? "positive" : "warning"} />}
              />
              <MetaRow
                label="Inbound ready"
                value={<StatusPill label={mailSettings.health.inbound_ready ? "Sí" : "No"} tone={mailSettings.health.inbound_ready ? "positive" : "warning"} />}
              />
              <MetaRow
                label="Última sync inbound"
                value={
                  mailSettings.inbound.last_sync ? (
                    <div className="space-y-1">
                      <div>{mailSettings.inbound.last_sync.status}</div>
                      <div className="text-xs font-normal text-slate-500">
                        {mailSettings.inbound.last_sync.at ? (
                          <RelativeTime date={mailSettings.inbound.last_sync.at} />
                        ) : (
                          "Sin timestamp"
                        )}
                      </div>
                    </div>
                  ) : (
                    "Nunca"
                  )
                }
              />
              {mailSettings.inbound.last_sync && (
                <div className="mt-4 rounded-2xl border border-slate-100 bg-slate-50/70 px-4 py-4">
                  <div className="flex items-center gap-2 text-sm font-medium text-slate-900">
                    <Mail className="h-4 w-4" />
                    Última sync persistida
                  </div>
                  <div className="mt-3 grid grid-cols-2 gap-3 text-sm text-slate-600">
                    <div className="rounded-xl bg-white px-3 py-2">
                      <p className="text-xs text-slate-500">Fetched</p>
                      <p className="font-semibold text-slate-900">{mailSettings.inbound.last_sync.counts.fetched}</p>
                    </div>
                    <div className="rounded-xl bg-white px-3 py-2">
                      <p className="text-xs text-slate-500">New</p>
                      <p className="font-semibold text-slate-900">{mailSettings.inbound.last_sync.counts.new}</p>
                    </div>
                    <div className="rounded-xl bg-white px-3 py-2">
                      <p className="text-xs text-slate-500">Deduplicated</p>
                      <p className="font-semibold text-slate-900">{mailSettings.inbound.last_sync.counts.deduplicated}</p>
                    </div>
                    <div className="rounded-xl bg-white px-3 py-2">
                      <p className="text-xs text-slate-500">Matched</p>
                      <p className="font-semibold text-slate-900">{mailSettings.inbound.last_sync.counts.matched}</p>
                    </div>
                    <div className="rounded-xl bg-white px-3 py-2">
                      <p className="text-xs text-slate-500">Unmatched</p>
                      <p className="font-semibold text-slate-900">{mailSettings.inbound.last_sync.counts.unmatched}</p>
                    </div>
                    <div className="rounded-xl bg-white px-3 py-2">
                      <p className="text-xs text-slate-500">Status</p>
                      <p className="font-semibold text-slate-900">{mailSettings.inbound.last_sync.status}</p>
                    </div>
                  </div>
                  {mailSettings.inbound.last_sync.error && (
                    <p className="mt-3 text-sm text-rose-600">{mailSettings.inbound.last_sync.error}</p>
                  )}
                </div>
              )}
            </SectionCard>

            <SectionCard
              title="Límites y seguridad"
              description="Qué se puede ver desde la app y qué sigue fuera de la UI."
            >
              <div className="flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-4">
                <Lock className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
                <div className="space-y-2 text-sm text-amber-900">
                  <p className="font-medium">Secrets siguen fuera de Settings</p>
                  <p>
                    SMTP password, IMAP password, OAuth tokens, API keys y demás secretos permanecen en env o
                    secret store local. Esta pantalla solo muestra readiness y configuración operativa no sensible.
                  </p>
                </div>
              </div>
            </SectionCard>
          </div>
        </div>
      )}
    </div>
  );
}

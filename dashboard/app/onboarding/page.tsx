"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  ExternalLink,
  Loader2,
  Play,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
  WandSparkles,
} from "lucide-react";
import { sileo } from "sileo";
import { PageHeader } from "@/components/layout/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { BrandSection } from "@/components/settings/brand-section";
import { CredentialsSection } from "@/components/settings/credentials-section";
import { MailInboundSection } from "@/components/settings/mail-inbound-section";
import { MailOutboundSection } from "@/components/settings/mail-outbound-section";
import { RulesSection } from "@/components/settings/rules-section";
import { WhatsAppSection } from "@/components/settings/whatsapp-section";
import { TelegramSection } from "@/components/settings/telegram-section";
import {
  runSetupAction,
} from "@/lib/api/client";
import { useApi } from "@/lib/hooks/use-swr-fetch";
import type {
  MailCredentials,
  MailSettings,
  OperationalSettings,
  SetupAction,
  SetupReadiness,
  SetupReadinessStep,
  WhatsAppCredentials,
} from "@/types";
import type { TelegramCredentials } from "@/lib/api/client";

const STEP_LABELS: Record<string, string> = {
  setup: "Preparar entorno",
  brand: "Marca y firma",
  whatsapp: "WhatsApp",
  credentials: "Email (SMTP)",
  mail_out: "Mail de salida",
  mail_in: "Mail de entrada",
  telegram: "Notificaciones",
  rules: "Reglas",
  done: "Listo para usar",
};

export default function OnboardingPage() {
  const searchParams = useSearchParams();
  const rawNextPath = searchParams.get("next") || "/";
  const nextPath =
    rawNextPath.startsWith("/") && !rawNextPath.startsWith("//") && !rawNextPath.startsWith("/\\")
      ? rawNextPath
      : "/";

  const { data: readiness, isLoading: readinessLoading, error: readinessError, mutate: mutateReadiness } = useApi<SetupReadiness>("/setup/readiness");
  const { data: mailData, isLoading: mailLoading, mutate: mutateMail } = useApi<MailSettings>("/settings/mail");
  const { data: opData, mutate: mutateOp } = useApi<OperationalSettings>("/settings/operational");
  const { data: credsData, mutate: mutateCreds } = useApi<MailCredentials>("/settings/mail-credentials");
  const { data: waData, mutate: mutateWa } = useApi<WhatsAppCredentials>("/settings/whatsapp-credentials");
  const { data: tgData, mutate: mutateTg } = useApi<TelegramCredentials>("/settings/telegram-credentials");

  const loading = readinessLoading || mailLoading;
  const loadError = readinessError ? "No se pudo cargar el estado de onboarding." : null;

  const [activeStep, setActiveStep] = useState<string>("setup");
  const [runningAction, setRunningAction] = useState<string | null>(null);
  const [actionOutput, setActionOutput] = useState<Record<string, string | null>>({});

  const refresh = useCallback(async () => {
    await Promise.all([mutateReadiness(), mutateMail(), mutateOp(), mutateCreds(), mutateWa(), mutateTg()]);
  }, [mutateReadiness, mutateMail, mutateOp, mutateCreds, mutateWa, mutateTg]);

  const handleSavedOps = (updated: OperationalSettings) => {
    void mutateOp(updated, false);
    void refresh();
  };

  const handleSavedCreds = (updated: MailCredentials) => {
    void mutateCreds(updated, false);
    void refresh();
  };

  const handleSavedWa = (updated: WhatsAppCredentials) => {
    void mutateWa(updated, false);
    void refresh();
  };

  const handleSavedTg = (updated: TelegramCredentials) => {
    void mutateTg(updated, false);
    void refresh();
  };

  const handleAction = async (action: SetupAction) => {
    if (action.kind === "manual") return;
    setRunningAction(action.id);
    try {
      const result = await sileo.promise(runSetupAction(action.id).then((value) => {
        if (value.status !== "completed") {
          throw new Error(value.detail || value.summary);
        }
        return value;
      }), {
        loading: { title: `Ejecutando ${action.label}...` },
        success: { title: resultTitle(action.label, true) },
        error: (err: unknown) => ({
          title: resultTitle(action.label, false),
          description: err instanceof Error ? err.message : "Accion fallida.",
        }),
      });
      setActionOutput((prev) => ({ ...prev, [action.id]: result.stdout_tail ?? result.detail }));
      await refresh();
    } finally {
      setRunningAction(null);
    }
  };

  const flowSteps = useMemo(() => {
    const wizard = readiness?.wizard_steps ?? [];
    const base = ["setup", ...wizard];
    const deduped = Array.from(new Set(base));
    if (readiness?.dashboard_unlocked) deduped.push("done");
    return deduped;
  }, [readiness]);

  useEffect(() => {
    if (flowSteps.length === 0) return;
    if (!flowSteps.includes(activeStep)) {
      setActiveStep(flowSteps[0]);
    }
  }, [activeStep, flowSteps]);

  const activeIndex = flowSteps.indexOf(activeStep);
  const canGoBack = activeIndex > 0;
  const canGoNext = activeIndex >= 0 && activeIndex < flowSteps.length - 1;

  if (loading && !readiness) {
    return (
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-8 py-12 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Preparando onboarding profesional...
        </div>
      </div>
    );
  }

  if (loadError || !readiness || !mailData || !opData || !credsData) {
    return (
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-6xl px-8 py-10">
          <PageHeader
            title="Onboarding de Scouter"
            description="Deja el sistema listo antes de desbloquear el dashboard."
          />
          <div className="mt-6">
            <EmptyState
              icon={TriangleAlert}
              title="No se pudo cargar el onboarding"
              description={loadError ?? "Faltan datos para continuar."}
            />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto bg-background">
      <div className="mx-auto max-w-6xl px-8 py-10">
        <PageHeader
          title="Onboarding profesional"
          description="Primero deja Scouter listo. Despues desbloqueas dashboard + Hermes."
        />

        <div className="mt-6 grid gap-6 xl:grid-cols-[280px,1fr]">
          <aside className="space-y-4">
            <StatusCard readiness={readiness} />
            <nav className="rounded-2xl border border-border bg-card p-3 shadow-sm">
              <div className="mb-3 flex items-center gap-2 px-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                <WandSparkles className="h-3.5 w-3.5" />
                Flujo recomendado
              </div>
              <div className="space-y-1.5">
                {flowSteps.map((stepId, index) => (
                  <button
                    key={stepId}
                    type="button"
                    onClick={() => setActiveStep(stepId)}
                    className={`w-full rounded-xl px-3 py-2 text-left text-sm transition ${
                      activeStep === stepId
                        ? "bg-foreground text-background"
                        : "bg-muted/70 text-muted-foreground hover:bg-muted hover:text-foreground"
                    }`}
                  >
                    <div className="text-[11px] uppercase tracking-wide opacity-70">Paso {index + 1}</div>
                    <div className="font-medium">{STEP_LABELS[stepId] ?? stepId}</div>
                  </button>
                ))}
              </div>
            </nav>
            <UpdatesCard readiness={readiness} />
          </aside>

          <section className="space-y-6">
            {activeStep === "setup" && (
              <SetupStage
                readiness={readiness}
                onAction={handleAction}
                runningAction={runningAction}
                actionOutput={actionOutput}
              />
            )}
            {activeStep === "brand" && <BrandSection data={opData} onSaved={handleSavedOps} />}
            {activeStep === "whatsapp" && waData && (
              <WhatsAppSection data={waData} onSaved={handleSavedWa} />
            )}
            {activeStep === "credentials" && (
              <CredentialsSection data={credsData} onSaved={handleSavedCreds} />
            )}
            {activeStep === "mail_out" && (
              <MailOutboundSection data={opData} mailData={mailData} onSaved={handleSavedOps} />
            )}
            {activeStep === "mail_in" && (
              <MailInboundSection data={opData} mailData={mailData} onSaved={handleSavedOps} />
            )}
            {activeStep === "telegram" && tgData && (
              <TelegramSection data={tgData} onSaved={handleSavedTg} />
            )}
            {activeStep === "rules" && <RulesSection data={opData} onSaved={handleSavedOps} />}
            {activeStep === "done" && <ReadyStage nextPath={nextPath} />}

            <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border bg-card px-5 py-4 shadow-sm">
              <button
                type="button"
                onClick={() => canGoBack && setActiveStep(flowSteps[activeIndex - 1])}
                disabled={!canGoBack}
                className="inline-flex items-center gap-2 rounded-xl border border-border px-3 py-2 text-sm text-muted-foreground transition hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
              >
                <ArrowLeft className="h-4 w-4" />
                Anterior
              </button>
              <div className="text-xs text-muted-foreground">
                {readiness.dashboard_unlocked
                  ? "Dashboard desbloqueado"
                  : `Estado actual: ${readiness.summary}`}
              </div>
              <button
                type="button"
                onClick={() => canGoNext && setActiveStep(flowSteps[activeIndex + 1])}
                disabled={!canGoNext}
                className="inline-flex items-center gap-2 rounded-xl bg-foreground px-3 py-2 text-sm font-medium text-background transition hover:bg-foreground/80 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Siguiente
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

function resultTitle(label: string, ok: boolean) {
  return ok ? `${label} terminado` : `${label} fallo`;
}

function StatusCard({ readiness }: { readiness: SetupReadiness }) {
  const tone =
    readiness.overall === "ready"
      ? "border-emerald-200 bg-emerald-50 dark:bg-emerald-950/20"
      : readiness.overall === "config_required"
        ? "border-amber-200 bg-amber-50 dark:bg-amber-950/20"
        : "border-border bg-card";

  return (
    <div className={`rounded-2xl border p-5 shadow-sm ${tone}`}>
      <div className="flex items-start gap-3">
        <div className="rounded-xl bg-foreground p-2 text-background">
          <ShieldCheck className="h-4 w-4" />
        </div>
        <div>
          <p className="text-sm font-semibold text-foreground">Estado del onboarding</p>
          <p className="mt-1 text-sm text-muted-foreground">{readiness.summary}</p>
          <div className="mt-3 text-xs text-muted-foreground">
            Plataforma objetivo: <span className="font-medium text-foreground">{readiness.target_platform}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function UpdatesCard({ readiness }: { readiness: SetupReadiness }) {
  if (!readiness.updates) return null;
  return (
    <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
      <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-foreground">
        <RefreshCw className="h-4 w-4 text-foreground" />
        Updates
      </div>
      <p className="text-xs text-muted-foreground">{readiness.updates.detail}</p>
      <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
        <span className="rounded-full bg-muted px-2.5 py-1">branch: {readiness.updates.current_branch ?? "unknown"}</span>
        <span className="rounded-full bg-muted px-2.5 py-1">
          {readiness.updates.updates_available ? "hay updates" : "sin updates remotos"}
        </span>
        <span className="rounded-full bg-muted px-2.5 py-1">
          {readiness.updates.dirty ? "working tree dirty" : "working tree clean"}
        </span>
      </div>
    </div>
  );
}

function SetupStage({
  readiness,
  onAction,
  runningAction,
  actionOutput,
}: {
  readiness: SetupReadiness;
  onAction: (action: SetupAction) => Promise<void>;
  runningAction: string | null;
  actionOutput: Record<string, string | null>;
}) {
  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
        <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-foreground">
          <Sparkles className="h-4 w-4 text-foreground" />
          Preparar entorno y runtime
        </div>
        <div className="grid gap-4 lg:grid-cols-3">
          <ReadinessGroup title="Plataforma" steps={readiness.platform_steps} />
          <ReadinessGroup title="Runtime" steps={readiness.runtime_steps} />
          <ReadinessGroup title="Configuracion" steps={readiness.config_steps} />
        </div>
      </div>

      <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
        <div className="mb-4 text-sm font-semibold text-foreground">Acciones disponibles</div>
        <div className="space-y-3">
          {readiness.actions.map((action) => (
            <div key={action.id} className="rounded-2xl border border-border bg-muted/40 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-foreground">{action.label}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{action.description}</p>
                  {action.manual_instructions && (
                    <p className="mt-2 text-xs text-muted-foreground">{action.manual_instructions}</p>
                  )}
                </div>
                {action.kind === "api" ? (
                  <button
                    type="button"
                    onClick={() => void onAction(action)}
                    disabled={runningAction === action.id}
                    className="inline-flex items-center gap-2 rounded-xl bg-foreground px-3 py-2 text-sm font-medium text-background transition hover:bg-foreground/80 disabled:opacity-50"
                  >
                    {runningAction === action.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Play className="h-4 w-4" />
                    )}
                    {runningAction === action.id ? "Ejecutando..." : "Ejecutar"}
                  </button>
                ) : (
                  <span className="inline-flex items-center gap-2 rounded-xl border border-border px-3 py-2 text-xs text-muted-foreground">
                    <ExternalLink className="h-3.5 w-3.5" />
                    Accion manual guiada
                  </span>
                )}
              </div>
              {actionOutput[action.id] && (
                <pre className="mt-3 overflow-x-auto rounded-xl bg-background p-3 text-[11px] text-muted-foreground whitespace-pre-wrap">
                  {actionOutput[action.id]}
                </pre>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ReadinessGroup({ title, steps }: { title: string; steps: SetupReadinessStep[] }) {
  return (
    <div className="rounded-2xl border border-border bg-muted/30 p-4">
      <div className="mb-3 text-sm font-semibold text-foreground">{title}</div>
      <div className="space-y-2">
        {steps.map((step) => {
          const icon =
            step.status === "complete" ? (
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            ) : step.status === "warning" ? (
              <TriangleAlert className="h-4 w-4 text-amber-500" />
            ) : (
              <TriangleAlert className="h-4 w-4 text-rose-400" />
            );
          return (
            <div key={step.id} className="rounded-xl bg-background px-3 py-2">
              <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                {icon}
                {step.label}
              </div>
              {step.detail && <p className="mt-1 text-xs text-muted-foreground">{step.detail}</p>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ReadyStage({ nextPath }: { nextPath: string }) {
  return (
    <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-6 shadow-sm dark:bg-emerald-950/20">
      <div className="flex items-start gap-3">
        <div className="rounded-xl bg-emerald-600 p-2 text-white">
          <CheckCircle2 className="h-5 w-5" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-foreground">Scouter quedo listo</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            El dashboard ya esta desbloqueado y Hermes puede usarse sin pelearte con setup manual.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <Link
              href={nextPath}
              className="inline-flex items-center gap-2 rounded-xl bg-foreground px-4 py-2 text-sm font-medium text-background transition hover:bg-foreground/80"
            >
              Ir al dashboard
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/settings"
              className="inline-flex items-center gap-2 rounded-xl border border-border px-4 py-2 text-sm text-muted-foreground transition hover:text-foreground"
            >
              Abrir configuracion
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

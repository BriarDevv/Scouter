"use client";

import {
  ArrowRight,
  CheckCircle2,
  Circle,
  TriangleAlert,
  XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { SetupStatus } from "@/types";
import type { EmailSubTab, TabId } from "./types";

interface SetupChecklistProps {
  data: SetupStatus;
  onTabChange: (tab: TabId, subTab?: string) => void;
}

interface ActionTarget {
  tab: TabId;
  subTab?: EmailSubTab;
}

const actionTabMap: Record<string, ActionTarget> = {
  brand: { tab: "identity" },
  credentials: { tab: "email", subTab: "credentials" },
  mail_out: { tab: "email", subTab: "mail" },
  mail_in: { tab: "email", subTab: "mail" },
  rules: { tab: "ai" },
};

type StepStatus = "complete" | "warning" | "incomplete" | "pending";

const STATUS_STYLES: Record<
  StepStatus,
  { card: string; iconColor: string; iconBg: string; chip: string; chipText: string }
> = {
  complete: {
    card: "border-emerald-200 bg-emerald-50 dark:border-emerald-900/40 dark:bg-emerald-950/20",
    iconColor: "text-emerald-600 dark:text-emerald-400",
    iconBg: "bg-emerald-100 dark:bg-emerald-900/40",
    chip: "bg-emerald-100/80 dark:bg-emerald-900/40",
    chipText: "text-emerald-700 dark:text-emerald-300",
  },
  warning: {
    card: "border-amber-200 bg-amber-50 dark:border-amber-900/40 dark:bg-amber-950/20",
    iconColor: "text-amber-600 dark:text-amber-400",
    iconBg: "bg-amber-100 dark:bg-amber-900/40",
    chip: "bg-amber-100/80 dark:bg-amber-900/40",
    chipText: "text-amber-700 dark:text-amber-300",
  },
  incomplete: {
    card: "border-rose-200 bg-rose-50 dark:border-rose-900/40 dark:bg-rose-950/20",
    iconColor: "text-rose-600 dark:text-rose-400",
    iconBg: "bg-rose-100 dark:bg-rose-900/40",
    chip: "bg-rose-100/80 dark:bg-rose-900/40",
    chipText: "text-rose-700 dark:text-rose-300",
  },
  pending: {
    card: "border-border bg-muted/40",
    iconColor: "text-muted-foreground",
    iconBg: "bg-muted",
    chip: "bg-muted",
    chipText: "text-muted-foreground",
  },
};

const STATUS_LABEL: Record<StepStatus, string> = {
  complete: "Listo",
  warning: "Atención",
  incomplete: "Falta",
  pending: "Pendiente",
};

export function SetupChecklist({ data, onTabChange }: SetupChecklistProps) {
  const total = data.steps.length;
  const completed = data.steps.filter((s) => s.status === "complete").length;
  const pending = data.steps.filter((s) => s.status !== "complete");
  const pct = total > 0 ? (completed / total) * 100 : 0;

  const overallLabel =
    data.overall === "ready"
      ? "Sistema listo para operar"
      : data.overall === "warning"
        ? "Listo con advertencias"
        : "Configuración incompleta";

  const overallIcon =
    data.overall === "ready" ? (
      <CheckCircle2 className="h-5 w-5 text-emerald-500" />
    ) : data.overall === "warning" ? (
      <TriangleAlert className="h-5 w-5 text-amber-500" />
    ) : (
      <XCircle className="h-5 w-5 text-rose-500" />
    );

  const overallBarColor =
    data.overall === "ready"
      ? "bg-emerald-500"
      : data.overall === "warning"
        ? "bg-amber-500"
        : "bg-rose-500";

  return (
    <div className="space-y-6">
      {/* ═══════════════════════════════════════════════════════
          HERO COMMAND BAR
          ═══════════════════════════════════════════════════════ */}
      <div className="space-y-4 rounded-2xl border border-border bg-card p-5">
        {/* Status row: icon + label + progress bar */}
        <div className="flex items-start gap-4">
          <div className="mt-0.5 shrink-0">{overallIcon}</div>
          <div className="min-w-0 flex-1 space-y-2">
            <div className="flex items-baseline justify-between gap-3">
              <p className="font-heading text-base font-semibold text-foreground">
                {overallLabel}
              </p>
              <p className="shrink-0 font-data text-[11px] text-muted-foreground">
                <span className="text-foreground/80">
                  {completed}/{total}
                </span>{" "}
                · {Math.round(pct)}%
              </p>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-muted">
              <div
                className={cn(
                  "h-full rounded-full transition-[width] duration-500",
                  overallBarColor
                )}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        </div>

        {/* Pending actions row (only if there are pending) */}
        {pending.length > 0 && (
          <div className="space-y-2 border-t border-border/60 pt-4">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Próximas acciones
            </p>
            <div className="flex flex-wrap gap-1.5">
              {pending.slice(0, 6).map((step) => {
                const target = actionTabMap[step.id];
                const dotColor =
                  step.status === "incomplete"
                    ? "bg-rose-500"
                    : step.status === "warning"
                      ? "bg-amber-500"
                      : "bg-muted-foreground/40";

                if (!target) {
                  return (
                    <span
                      key={step.id}
                      className="inline-flex items-center gap-1.5 rounded-md border border-border/60 bg-muted/40 px-2.5 py-1 text-[11px] text-muted-foreground"
                    >
                      <span className={cn("h-1.5 w-1.5 rounded-full", dotColor)} />
                      {step.label}
                    </span>
                  );
                }
                return (
                  <button
                    key={step.id}
                    type="button"
                    onClick={() => onTabChange(target.tab, target.subTab)}
                    className="group inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-2.5 py-1 text-[11px] font-medium text-foreground transition-colors hover:bg-muted active:translate-y-px"
                  >
                    <span className={cn("h-1.5 w-1.5 rounded-full", dotColor)} />
                    {step.label}
                    <ArrowRight className="h-3 w-3 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
                  </button>
                );
              })}
              {pending.length > 6 && (
                <span className="inline-flex items-center px-1 text-[10px] text-muted-foreground">
                  +{pending.length - 6} más
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ═══════════════════════════════════════════════════════
          STEPS GRID
          ═══════════════════════════════════════════════════════ */}
      <div className="space-y-3">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          Pasos de configuración
        </p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {data.steps.map((step) => {
            const target = actionTabMap[step.id];
            const status = (step.status as StepStatus) ?? "pending";
            const styles = STATUS_STYLES[status] ?? STATUS_STYLES.pending;
            const isComplete = status === "complete";

            const StatusIcon =
              status === "complete"
                ? CheckCircle2
                : status === "warning"
                  ? TriangleAlert
                  : status === "incomplete"
                    ? XCircle
                    : Circle;

            return (
              <div
                key={step.id}
                className={cn(
                  "group flex flex-col gap-3 rounded-2xl border p-4 transition-colors",
                  styles.card
                )}
              >
                <div className="flex items-start gap-3">
                  <div
                    className={cn(
                      "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
                      styles.iconBg
                    )}
                  >
                    <StatusIcon className={cn("h-4 w-4", styles.iconColor)} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm font-semibold leading-tight text-foreground">
                        {step.label}
                      </p>
                      <span
                        className={cn(
                          "shrink-0 rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider",
                          styles.chip,
                          styles.chipText
                        )}
                      >
                        {STATUS_LABEL[status]}
                      </span>
                    </div>
                    {step.detail && (
                      <p className="mt-1 line-clamp-2 text-[11px] text-muted-foreground">
                        {step.detail}
                      </p>
                    )}
                  </div>
                </div>

                {step.action && target && (
                  <button
                    type="button"
                    onClick={() => onTabChange(target.tab, target.subTab)}
                    className={cn(
                      "mt-auto inline-flex items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors active:translate-y-px",
                      isComplete
                        ? "border border-border/60 bg-card/70 text-muted-foreground hover:bg-card hover:text-foreground"
                        : "bg-foreground text-background hover:bg-foreground/80"
                    )}
                  >
                    {step.action}
                    <ArrowRight className="h-3 w-3" />
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}


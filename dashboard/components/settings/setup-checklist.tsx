"use client";

import { CheckCircle2, TriangleAlert, XCircle } from "lucide-react";
import type { SetupStatus } from "@/types";
import type { TabId } from "./types";

interface SetupChecklistProps {
  data: SetupStatus;
  onTabChange: (tab: TabId) => void;
}

export function SetupChecklist({ data, onTabChange }: SetupChecklistProps) {
  const statusIcon = (s: string) => {
    if (s === "complete") return <CheckCircle2 className="h-5 w-5 text-emerald-500" />;
    if (s === "warning") return <TriangleAlert className="h-5 w-5 text-amber-500" />;
    if (s === "incomplete") return <XCircle className="h-5 w-5 text-rose-400" />;
    return <div className="h-5 w-5 rounded-full border-2 border-border" />;
  };

  const actionTabMap: Record<string, TabId> = {
    brand: "brand",
    credentials: "credentials",
    mail_out: "mail_out",
    mail_in: "mail_in",
    rules: "rules",
  };

  const overallBg =
    data.overall === "ready"
      ? "bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200"
      : data.overall === "warning"
        ? "bg-amber-50 dark:bg-amber-950/30 border-amber-200"
        : "bg-muted border-border";

  const overallLabel =
    data.overall === "ready"
      ? "Sistema listo para operar"
      : data.overall === "warning"
        ? "Listo con advertencias"
        : "Configuración incompleta";

  const overallText =
    data.overall === "ready"
      ? "text-emerald-700"
      : data.overall === "warning"
        ? "text-amber-700"
        : "text-muted-foreground";

  return (
    <div className="space-y-6">
      <div className={`rounded-2xl border p-5 ${overallBg}`}>
        <div className="flex items-center gap-3">
          {data.overall === "ready" ? (
            <CheckCircle2 className="h-6 w-6 text-emerald-500" />
          ) : data.overall === "warning" ? (
            <TriangleAlert className="h-6 w-6 text-amber-500" />
          ) : (
            <XCircle className="h-6 w-6 text-rose-400" />
          )}
          <div>
            <p className={`font-semibold ${overallText}`}>{overallLabel}</p>
            <div className="mt-1 flex gap-3 text-xs">
              <span className={data.ready_to_send ? "text-emerald-600" : "text-muted-foreground"}>
                {data.ready_to_send ? "✓" : "○"} Envío listo
              </span>
              <span className={data.ready_to_receive ? "text-emerald-600" : "text-muted-foreground"}>
                {data.ready_to_receive ? "✓" : "○"} Recepción lista
              </span>
            </div>
          </div>
        </div>
      </div>
      <div className="space-y-3">
        {data.steps.map((step) => (
          <div
            key={step.id}
            className="flex items-start gap-4 rounded-2xl border border-border bg-card p-4"
          >
            <div className="mt-0.5 shrink-0">{statusIcon(step.status)}</div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-foreground">{step.label}</p>
              {step.detail && (
                <p className="mt-0.5 text-xs text-muted-foreground">{step.detail}</p>
              )}
            </div>
            {step.action && actionTabMap[step.id] && (
              <button
                type="button"
                onClick={() => onTabChange(actionTabMap[step.id])}
                className="shrink-0 rounded-xl border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground transition hover:border-border hover:text-foreground"
              >
                {step.action}
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

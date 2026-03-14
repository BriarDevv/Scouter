"use client";

import { Bot, BrainCircuit, Cpu, Settings, ShieldCheck } from "lucide-react";
import { SettingsSectionCard, MetaRow } from "./settings-primitives";
import type { LLMSettings } from "@/types";

export function LLMSection({ data }: { data: LLMSettings }) {
  return (
    <div className="grid gap-6 lg:grid-cols-[1.2fr,0.8fr]">
      <SettingsSectionCard
        title="Modelos activos"
        description="Configuración LLM read-only desde env."
        icon={Bot}
      >
        <div className="space-y-3">
          {[
            { label: "Leader", model: data.leader_model, Icon: BrainCircuit },
            { label: "Executor", model: data.executor_model, Icon: Cpu },
            { label: "Reviewer", model: data.reviewer_model, Icon: ShieldCheck },
          ].map(({ label, model, Icon }) => (
            <div
              key={label}
              className="flex items-center justify-between rounded-2xl border border-border bg-muted/70 px-4 py-3"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-foreground text-white">
                  <Icon className="h-4 w-4" />
                </div>
                <span className="text-sm font-medium text-foreground">{label}</span>
              </div>
              <code className="rounded-lg bg-card px-3 py-1.5 text-sm text-foreground/80 shadow-sm">
                {model ?? "No configurado"}
              </code>
            </div>
          ))}
        </div>
      </SettingsSectionCard>
      <SettingsSectionCard title="Detalles" icon={Settings}>
        <MetaRow label="Provider" value={data.provider} />
        <MetaRow label="Base URL" value={<code className="text-xs">{data.base_url}</code>} />
        <MetaRow label="Timeout" value={`${data.timeout_seconds}s`} />
        <MetaRow label="Reintentos" value={data.max_retries} />
        <MetaRow
          label="Catálogo"
          value={
            <div className="flex flex-wrap justify-end gap-1">
              {data.supported_models.map((m) => (
                <code
                  key={m}
                  className="rounded-lg bg-muted px-2 py-0.5 text-xs text-foreground/80"
                >
                  {m}
                </code>
              ))}
            </div>
          }
        />
      </SettingsSectionCard>
    </div>
  );
}

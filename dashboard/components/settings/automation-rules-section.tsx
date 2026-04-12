"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Cpu } from "lucide-react";
import {
  FieldRow,
  SectionFooter,
  SectionSubheading,
  SettingsSectionCard,
  TextInput,
  Toggle,
  ToggleListItem,
  useSave,
} from "./settings-primitives";
import { apiFetch } from "@/lib/api/client";
import type { OperationalSettings } from "@/types";

interface ResourceModeStatus {
  db_value: boolean | null;
  env_value: boolean;
  desired: boolean;
  runtime: boolean;
  restart_required: boolean;
}

interface AutomationRulesSectionProps {
  data: OperationalSettings;
  onSaved: (updated: OperationalSettings) => void;
}

type AutoRuleKey = "reply_assistant_enabled" | "reviewer_enabled";

const CROSS_CHANNEL_RULES: { key: AutoRuleKey; label: string; hint: string }[] = [
  {
    key: "reply_assistant_enabled",
    label: "Asistente de respuesta",
    hint: "Borradores automáticos para mensajes entrantes",
  },
  {
    key: "reviewer_enabled",
    label: "Revisor automático",
    hint: "Revisión profunda por el modelo reviewer",
  },
];

export function AutomationRulesSection({ data, onSaved }: AutomationRulesSectionProps) {
  const [resourceMode, setResourceMode] = useState<ResourceModeStatus | null>(null);

  useEffect(() => {
    apiFetch<ResourceModeStatus>("/settings/resource-mode")
      .then(setResourceMode)
      .catch(() => {});
  }, [data]);

  const [form, setForm] = useState({
    reply_assistant_enabled: data.reply_assistant_enabled,
    reviewer_enabled: data.reviewer_enabled,
    reviewer_confidence_threshold: String(data.reviewer_confidence_threshold),
    low_resource_mode: data.low_resource_mode ?? false,
  });

  const set = (k: keyof typeof form) => (v: string | boolean) =>
    setForm((prev) => ({ ...prev, [k]: v }));

  const getData = useCallback(
    () => ({
      reply_assistant_enabled: form.reply_assistant_enabled,
      reviewer_enabled: form.reviewer_enabled,
      reviewer_confidence_threshold:
        parseFloat(form.reviewer_confidence_threshold) || 0.7,
      low_resource_mode: form.low_resource_mode,
    }),
    [form]
  );

  const { save, saving } = useSave(getData, onSaved);

  return (
    <div className="space-y-4">
      <SettingsSectionCard title="Inteligencia artificial" icon={Cpu}>
        <div className="space-y-5">
          <div className="space-y-2">
            <SectionSubheading>Asistente y revisor</SectionSubheading>
            <div className="grid gap-1 sm:grid-cols-2">
              {CROSS_CHANNEL_RULES.map((rule) => (
                <ToggleListItem
                  key={rule.key}
                  label={rule.label}
                  hint={rule.hint}
                  checked={Boolean(form[rule.key])}
                  onChange={(v) => set(rule.key)(v)}
                />
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <SectionSubheading>Umbrales</SectionSubheading>
            <FieldRow label="Umbral de confianza del revisor">
              <TextInput
                value={form.reviewer_confidence_threshold}
                onChange={set("reviewer_confidence_threshold")}
                placeholder="0.7"
                type="number"
              />
            </FieldRow>
          </div>

          <div className="space-y-2">
            <SectionSubheading>Recursos</SectionSubheading>
            <div className="flex flex-wrap items-center gap-x-6 gap-y-3 rounded-xl border border-border/60 bg-muted/30 px-4 py-3">
              <Toggle
                checked={form.low_resource_mode}
                onChange={set("low_resource_mode") as (v: boolean) => void}
                label={form.low_resource_mode ? "Modo bajo recurso" : "Modo normal"}
              />
            </div>
          </div>
        </div>

        {resourceMode?.restart_required && (
          <div className="mt-4 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-200">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <p className="font-medium">Reinicio de workers requerido</p>
              <p className="mt-0.5 text-[11px] opacity-80">
                El modo de recursos cambió pero los workers siguen con la config
                anterior. Ejecutá{" "}
                <code className="rounded bg-amber-100 px-1 font-data dark:bg-amber-900/30">
                  make restart-workers
                </code>{" "}
                para aplicar.
              </p>
            </div>
          </div>
        )}
      </SettingsSectionCard>
      <SectionFooter
        updatedAt={data.updated_at}
        onSave={save}
        saving={saving}
      />
    </div>
  );
}

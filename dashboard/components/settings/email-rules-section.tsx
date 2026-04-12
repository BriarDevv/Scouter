"use client";

import { useCallback, useState } from "react";
import { ListChecks } from "lucide-react";
import {
  SectionFooter,
  SectionSubheading,
  SettingsSectionCard,
  ToggleListItem,
  useSave,
} from "./settings-primitives";
import type { OperationalSettings } from "@/types";

interface EmailRulesSectionProps {
  data: OperationalSettings;
  onSaved: (updated: OperationalSettings) => void;
}

type EmailRuleKey =
  | "require_approved_drafts"
  | "auto_classify_inbound"
  | "prioritize_quote_replies"
  | "prioritize_meeting_replies"
  | "allow_reply_assistant_generation";

const EMAIL_RULES: { key: EmailRuleKey; label: string; hint: string }[] = [
  {
    key: "require_approved_drafts",
    label: "Requerir aprobación de drafts",
    hint: "Solo los drafts aprobados se pueden enviar",
  },
  {
    key: "auto_classify_inbound",
    label: "Clasificar replies al sync",
    hint: "Clasificación automática de bandeja de entrada",
  },
  {
    key: "prioritize_quote_replies",
    label: "Priorizar cotizaciones",
    hint: "Replies con pedido de cotización al tope de la cola",
  },
  {
    key: "prioritize_meeting_replies",
    label: "Priorizar reuniones",
    hint: "Replies con pedido de reunión al tope de la cola",
  },
  {
    key: "allow_reply_assistant_generation",
    label: "Generación asistida",
    hint: "Permite que el asistente genere respuestas nuevas",
  },
];

export function EmailRulesSection({ data, onSaved }: EmailRulesSectionProps) {
  const [form, setForm] = useState({
    require_approved_drafts: data.require_approved_drafts,
    auto_classify_inbound: data.auto_classify_inbound,
    prioritize_quote_replies: data.prioritize_quote_replies,
    prioritize_meeting_replies: data.prioritize_meeting_replies,
    allow_reply_assistant_generation: data.allow_reply_assistant_generation,
  });

  const set = (k: EmailRuleKey) => (v: boolean) =>
    setForm((prev) => ({ ...prev, [k]: v }));

  const getData = useCallback(
    (): Partial<OperationalSettings> => ({ ...form }),
    [form]
  );

  const { save, saving } = useSave(getData, onSaved);

  return (
    <div className="space-y-4">
      <SettingsSectionCard
        title="Reglas de email"
        description="Comportamiento del pipeline de mail (envío, clasificación y priorización de respuestas)."
        icon={ListChecks}
      >
        <div className="space-y-2">
          <SectionSubheading>Reglas activas</SectionSubheading>
          <div className="grid gap-1 sm:grid-cols-2">
            {EMAIL_RULES.map((rule) => (
              <ToggleListItem
                key={rule.key}
                label={rule.label}
                hint={rule.hint}
                checked={Boolean(form[rule.key])}
                onChange={set(rule.key)}
              />
            ))}
          </div>
        </div>
      </SettingsSectionCard>
      <SectionFooter
        updatedAt={data.updated_at}
        onSave={save}
        saving={saving}
      />
    </div>
  );
}

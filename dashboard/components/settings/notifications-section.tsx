"use client";

import { useCallback, useState } from "react";
import { BellRing } from "lucide-react";
import {
  SettingsSectionCard,
  FieldRow,
  SectionSubheading,
  TextInput,
  Toggle,
  SectionFooter,
  Select,
  useSave,
} from "./settings-primitives";
import type { OperationalSettings } from "@/types";

interface NotificationsSectionProps {
  data: OperationalSettings;
  onSaved: (updated: OperationalSettings) => void;
}

export function NotificationsSection({ data, onSaved }: NotificationsSectionProps) {
  const [form, setForm] = useState({
    notifications_enabled: data.notifications_enabled ?? true,
    notification_score_threshold: String(data.notification_score_threshold ?? "70"),
    whatsapp_alerts_enabled: data.whatsapp_alerts_enabled ?? false,
    telegram_alerts_enabled: data.telegram_alerts_enabled ?? false,
    whatsapp_min_severity: data.whatsapp_min_severity ?? "high",
    notification_categories_business: (data.whatsapp_categories ?? ["business", "system"]).includes("business"),
    notification_categories_system: (data.whatsapp_categories ?? ["business", "system"]).includes("system"),
    notification_categories_security: (data.whatsapp_categories ?? []).includes("security"),
  });

  const set = (k: string) => (v: string | boolean) =>
    setForm((prev) => ({ ...prev, [k]: v }));

  const getData = useCallback(
    () => {
      const categories: string[] = [];
      if (form.notification_categories_business) categories.push("business");
      if (form.notification_categories_system) categories.push("system");
      if (form.notification_categories_security) categories.push("security");
      return {
        notifications_enabled: form.notifications_enabled,
        notification_score_threshold: parseInt(form.notification_score_threshold, 10) || 70,
        whatsapp_alerts_enabled: form.whatsapp_alerts_enabled,
        telegram_alerts_enabled: form.telegram_alerts_enabled,
        whatsapp_min_severity: form.whatsapp_min_severity,
        whatsapp_categories: categories,
      } as Partial<OperationalSettings>;
    },
    [form]
  );

  const { save, saving } = useSave(getData, onSaved);

  return (
    <div className="space-y-4">
      <SettingsSectionCard title="Notificaciones" icon={BellRing}>
        <div className="space-y-5">
          <div className="flex flex-wrap items-center gap-x-6 gap-y-3 rounded-xl border border-border/60 bg-muted/30 px-4 py-3">
            <Toggle
              checked={form.notifications_enabled}
              onChange={set("notifications_enabled") as (v: boolean) => void}
              label={form.notifications_enabled ? "Notificaciones habilitadas" : "Notificaciones deshabilitadas"}
            />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <div className="space-y-4">
              <div className="space-y-2">
                <SectionSubheading>Canales</SectionSubheading>
                <div className="flex flex-wrap items-center gap-x-6 gap-y-3 rounded-xl border border-border/60 bg-muted/30 px-4 py-3">
                  <Toggle
                    checked={form.whatsapp_alerts_enabled}
                    onChange={set("whatsapp_alerts_enabled") as (v: boolean) => void}
                    label="WhatsApp"
                  />
                  <Toggle
                    checked={form.telegram_alerts_enabled}
                    onChange={set("telegram_alerts_enabled") as (v: boolean) => void}
                    label="Telegram"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <SectionSubheading>Categorías</SectionSubheading>
                <div className="flex flex-col gap-3 rounded-xl border border-border/60 bg-muted/30 px-4 py-3">
                  <Toggle
                    checked={form.notification_categories_business}
                    onChange={set("notification_categories_business") as (v: boolean) => void}
                    label="Negocios (leads, outreach, respuestas)"
                  />
                  <Toggle
                    checked={form.notification_categories_system}
                    onChange={set("notification_categories_system") as (v: boolean) => void}
                    label="Sistema (errores, sincronización, tareas)"
                  />
                  <Toggle
                    checked={form.notification_categories_security}
                    onChange={set("notification_categories_security") as (v: boolean) => void}
                    label="Seguridad (accesos, credenciales, alertas)"
                  />
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <FieldRow label="Umbral de score">
                <TextInput
                  value={form.notification_score_threshold}
                  onChange={set("notification_score_threshold")}
                  placeholder="70"
                  type="number"
                  disabled={!form.notifications_enabled}
                />
              </FieldRow>
              <FieldRow label="Severidad mínima">
                <Select
                  value={form.whatsapp_min_severity}
                  onChange={set("whatsapp_min_severity") as (v: string) => void}
                  disabled={!form.notifications_enabled}
                >
                  <option value="info">Info</option>
                  <option value="warning">Warning</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </Select>
              </FieldRow>
            </div>
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

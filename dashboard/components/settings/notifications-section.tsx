"use client";

import { useCallback, useState } from "react";
import { BellRing } from "lucide-react";
import {
  SettingsSectionCard,
  FieldRow,
  TextInput,
  Toggle,
  SaveButton,
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
        whatsapp_min_severity: form.whatsapp_min_severity,
        whatsapp_categories: categories,
      } as Partial<OperationalSettings>;
    },
    [form]
  );

  const { save, saving } = useSave(getData, onSaved);

  return (
    <div className="space-y-6">
      <SettingsSectionCard
        title="Notificaciones"
        description="Configura las alertas y notificaciones del sistema. Recibe avisos cuando se detectan leads de alto puntaje u otros eventos importantes."
        icon={BellRing}
      >
        <div className="grid gap-0 lg:grid-cols-2 lg:gap-x-8">
          <div>
            <FieldRow label="Notificaciones habilitadas" hint="Activar o desactivar todas las notificaciones del sistema">
              <Toggle
                checked={form.notifications_enabled}
                onChange={set("notifications_enabled") as (v: boolean) => void}
                label={form.notifications_enabled ? "Habilitadas" : "Deshabilitadas"}
              />
            </FieldRow>
            <FieldRow label="Umbral de score para alertas" hint="Recibir alerta cuando un lead supere este puntaje (0-100)">
              <TextInput
                value={form.notification_score_threshold}
                onChange={set("notification_score_threshold")}
                placeholder="70"
                type="number"
                disabled={!form.notifications_enabled}
              />
            </FieldRow>
            <FieldRow label="Alertas WhatsApp habilitadas" hint="Enviar alertas de alta prioridad por WhatsApp">
              <Toggle
                checked={form.whatsapp_alerts_enabled}
                onChange={set("whatsapp_alerts_enabled") as (v: boolean) => void}
                label={form.whatsapp_alerts_enabled ? "Habilitadas" : "Deshabilitadas"}
              />
            </FieldRow>
          </div>
          <div>
            <FieldRow label="Severidad mínima" hint="Solo enviar notificaciones con esta severidad o superior">
              <select
                value={form.whatsapp_min_severity}
                onChange={(e) => set("whatsapp_min_severity")(e.target.value)}
                disabled={!form.notifications_enabled}
                className="w-full rounded-xl border border-border bg-muted px-3 py-2 text-sm text-foreground outline-none focus:border-border focus:bg-card disabled:opacity-50"
              >
                <option value="info">Info</option>
                <option value="warning">Warning</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </FieldRow>
            <FieldRow label="Categorías de notificaciones" hint="Seleccionar qué categorías de eventos generan notificaciones">
              <div className="space-y-3 pt-1">
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
            </FieldRow>
          </div>
        </div>
        <div className="mt-4 flex justify-end">
          <SaveButton onClick={save} saving={saving} />
        </div>
      </SettingsSectionCard>
    </div>
  );
}

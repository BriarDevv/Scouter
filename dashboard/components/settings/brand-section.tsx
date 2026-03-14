"use client";

import { useCallback, useState } from "react";
import { Building2 } from "lucide-react";
import {
  SettingsSectionCard,
  FieldRow,
  TextInput,
  Toggle,
  SaveButton,
  useSave,
} from "./settings-primitives";
import { SignaturePreview } from "./signature-preview";
import type { OperationalSettings } from "@/types";

interface BrandSectionProps {
  data: OperationalSettings;
  onSaved: (updated: OperationalSettings) => void;
}

export function BrandSection({ data, onSaved }: BrandSectionProps) {
  const [form, setForm] = useState({
    brand_name: data.brand_name ?? "",
    signature_name: data.signature_name ?? "",
    signature_role: data.signature_role ?? "",
    signature_company: data.signature_company ?? "",
    portfolio_url: data.portfolio_url ?? "",
    website_url: data.website_url ?? "",
    calendar_url: data.calendar_url ?? "",
    signature_cta: data.signature_cta ?? "",
    signature_include_portfolio: data.signature_include_portfolio,
    default_outreach_tone: data.default_outreach_tone,
    default_reply_tone: data.default_reply_tone,
    default_closing_line: data.default_closing_line ?? "",
  });

  const set = (k: string) => (v: string | boolean) =>
    setForm((prev) => ({ ...prev, [k]: v }));

  const getData = useCallback(
    () => ({
      brand_name: form.brand_name || null,
      signature_name: form.signature_name || null,
      signature_role: form.signature_role || null,
      signature_company: form.signature_company || null,
      portfolio_url: form.portfolio_url || null,
      website_url: form.website_url || null,
      calendar_url: form.calendar_url || null,
      signature_cta: form.signature_cta || null,
      signature_include_portfolio: form.signature_include_portfolio,
      default_outreach_tone: form.default_outreach_tone || "profesional",
      default_reply_tone: form.default_reply_tone || "profesional",
      default_closing_line: form.default_closing_line || null,
    }),
    [form]
  );

  const { save, saving } = useSave(getData, onSaved);

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr,0.65fr]">
      <SettingsSectionCard
        title="Marca / Firma"
        description="Datos del emisor que se inyectan en drafts de outreach y respuestas asistidas."
        icon={Building2}
      >
        <div className="grid gap-0 lg:grid-cols-2 lg:gap-x-8">
          <div>
            <FieldRow label="Nombre comercial" hint="Nombre de la marca o agencia">
              <TextInput
                value={form.brand_name}
                onChange={set("brand_name")}
                placeholder="ej. BriarDev"
              />
            </FieldRow>
            <FieldRow label="Nombre del firmante">
              <TextInput
                value={form.signature_name}
                onChange={set("signature_name")}
                placeholder="ej. Mateo"
              />
            </FieldRow>
            <FieldRow label="Rol / Cargo">
              <TextInput
                value={form.signature_role}
                onChange={set("signature_role")}
                placeholder="ej. Desarrollador Web"
              />
            </FieldRow>
            <FieldRow label="Empresa en firma">
              <TextInput
                value={form.signature_company}
                onChange={set("signature_company")}
                placeholder="ej. BriarDev"
              />
            </FieldRow>
            <FieldRow label="CTA corta" hint="Llamada a la acción al final del email">
              <TextInput
                value={form.signature_cta}
                onChange={set("signature_cta")}
                placeholder="ej. ¿Agendamos una charla de 15 min?"
              />
            </FieldRow>
            <FieldRow label="Línea de cierre" hint="Frase final antes de la firma">
              <TextInput
                value={form.default_closing_line}
                onChange={set("default_closing_line")}
                placeholder="ej. Quedo atento, saludos"
              />
            </FieldRow>
          </div>
          <div>
            <FieldRow label="Portfolio URL">
              <TextInput
                value={form.portfolio_url}
                onChange={set("portfolio_url")}
                placeholder="https://briardev.xyz/portfolio"
                type="url"
              />
            </FieldRow>
            <FieldRow label="Sitio web">
              <TextInput
                value={form.website_url}
                onChange={set("website_url")}
                placeholder="https://briardev.xyz"
                type="url"
              />
            </FieldRow>
            <FieldRow label="URL de calendario" hint="Calendly u otro link de agenda">
              <TextInput
                value={form.calendar_url}
                onChange={set("calendar_url")}
                placeholder="https://cal.com/..."
                type="url"
              />
            </FieldRow>
            <FieldRow label="Tono outreach">
              <select
                value={form.default_outreach_tone}
                onChange={(e) => set("default_outreach_tone")(e.target.value)}
                className="w-full rounded-xl border border-border bg-muted px-3 py-2 text-sm text-foreground outline-none focus:border-border focus:bg-card"
              >
                {["profesional", "cercano", "consultivo", "breve", "empático"].map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </FieldRow>
            <FieldRow label="Tono de respuestas">
              <select
                value={form.default_reply_tone}
                onChange={(e) => set("default_reply_tone")(e.target.value)}
                className="w-full rounded-xl border border-border bg-muted px-3 py-2 text-sm text-foreground outline-none focus:border-border focus:bg-card"
              >
                {["profesional", "cercano", "consultivo", "breve", "empático"].map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </FieldRow>
            <FieldRow label="Incluir portfolio en firma">
              <Toggle
                checked={form.signature_include_portfolio}
                onChange={set("signature_include_portfolio") as (v: boolean) => void}
                label={form.signature_include_portfolio ? "Sí" : "No"}
              />
            </FieldRow>
          </div>
        </div>
        <div className="mt-4 flex justify-end">
          <SaveButton onClick={save} saving={saving} />
        </div>
      </SettingsSectionCard>
      <SignaturePreview form={form} />
    </div>
  );
}

"use client";

import { useCallback, useState } from "react";
import { PenLine } from "lucide-react";
import {
  FieldRow,
  SectionFooter,
  SectionSubheading,
  SettingsSectionCard,
  TextInput,
  ToggleListItem,
  useSave,
} from "./settings-primitives";
import { SignaturePreview } from "./signature-preview";
import type { OperationalSettings } from "@/types";

interface EmailSignatureSectionProps {
  data: OperationalSettings;
  onSaved: (updated: OperationalSettings) => void;
}

export function EmailSignatureSection({
  data,
  onSaved,
}: EmailSignatureSectionProps) {
  const n = (v: string | null) => v ?? "";

  const [form, setForm] = useState({
    default_closing_line: n(data.default_closing_line),
    signature_cta: n(data.signature_cta),
    signature_include_portfolio: data.signature_include_portfolio,
  });

  const set =
    <K extends keyof typeof form>(k: K) =>
    (v: (typeof form)[K]) =>
      setForm((prev) => ({ ...prev, [k]: v }));

  const getData = useCallback(
    (): Partial<OperationalSettings> => ({
      default_closing_line: form.default_closing_line || null,
      signature_cta: form.signature_cta || null,
      signature_include_portfolio: form.signature_include_portfolio,
    }),
    [form]
  );

  const { save, saving } = useSave(getData, onSaved);

  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-2 lg:items-stretch">
      <SettingsSectionCard
        title="Firma del mensaje"
        description="Cómo cierra Mote cada email — línea de despedida, CTA y enlaces opcionales."
        icon={PenLine}
      >
        <div className="space-y-3">
          <FieldRow label="Línea de cierre">
            <TextInput
              value={form.default_closing_line}
              onChange={set("default_closing_line")}
              placeholder='ej: "Quedo a disposición para cualquier consulta."'
            />
          </FieldRow>
          <FieldRow label="Llamada a la acción">
            <TextInput
              value={form.signature_cta}
              onChange={set("signature_cta")}
              placeholder='ej: "¿Agendamos una charla?"'
            />
          </FieldRow>
          <ToggleListItem
            label="Incluir portfolio en la firma"
            hint="Agrega el link del portfolio configurado en Identidad al pie del email"
            checked={form.signature_include_portfolio}
            onChange={set("signature_include_portfolio")}
          />
        </div>
      </SettingsSectionCard>

      <SettingsSectionCard title="Vista previa">
        <div className="pt-4">
        <SignaturePreview
          brandName={data.brand_name ?? ""}
          signerName={data.signature_name ?? ""}
          signerRole={data.signature_role ?? ""}
          signerCompany={data.signature_company ?? ""}
          portfolioUrl={data.portfolio_url ?? ""}
          websiteUrl={data.website_url ?? ""}
          calendarUrl={data.calendar_url ?? ""}
          cta={form.signature_cta}
          closingLine={form.default_closing_line}
          includePortfolio={form.signature_include_portfolio}
        />
        </div>
      </SettingsSectionCard>
      </div>

      <SectionFooter
        updatedAt={data.updated_at}
        onSave={save}
        saving={saving}
      />
    </div>
  );
}

"use client";

import React, { useCallback, useState } from "react";
import { CalendarDays, ExternalLink, Globe } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  SectionFooter,
  SectionSubheading,
  SettingsSectionCard,
  useSave,
} from "./settings-primitives";
import type { OperationalSettings } from "@/types";

// ─── Types ────────────────────────────────────────────────────────────

export interface BrandSectionProps {
  data: OperationalSettings;
  onSaved: (updated: OperationalSettings) => void;
}

// ─── Tone constants ───────────────────────────────────────────────────

const TONE_OPTIONS = [
  { value: "profesional", label: "Profesional" },
  { value: "cercano",     label: "Cercano"     },
  { value: "consultivo",  label: "Consultivo"  },
  { value: "breve",       label: "Breve"       },
  { value: "empático",    label: "Empático"    },
] as const;

type ToneValue = (typeof TONE_OPTIONS)[number]["value"];

// ─── Inline input — monochromatic, matches panel density ──────────────

function IdentityInput({
  value,
  onChange,
  placeholder,
  icon: Icon,
  mono,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  icon?: React.ComponentType<{ className?: string }>;
  mono?: boolean;
}) {
  return (
    <div className="relative">
      {Icon && (
        <Icon className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/60" />
      )}
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={cn(
          "w-full rounded-lg border border-border bg-muted/40 dark:bg-input/30 py-2 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground/50 focus:border-ring focus:bg-card focus:ring-3 focus:ring-ring/30",
          Icon ? "pl-8 pr-3" : "px-3",
          mono && "font-data text-xs"
        )}
      />
    </div>
  );
}

// ─── Field — label + input wrapper ────────────────────────────────────

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-medium text-foreground/80">{label}</label>
      {children}
    </div>
  );
}

// ─── Tone chips ───────────────────────────────────────────────────────

function ToneChips({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: ToneValue) => void;
}) {
  return (
    <div className="flex flex-nowrap gap-1.5">
      {TONE_OPTIONS.map((opt) => {
        const active = value === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={cn(
              "whitespace-nowrap rounded-lg border px-2.5 py-1 text-[11px] font-medium transition-colors active:translate-y-px",
              active
                ? "border-foreground bg-foreground text-background"
                : "border-border bg-muted/40 text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

// ─── BrandSection ─────────────────────────────────────────────────────

export function BrandSection({
  data,
  onSaved,
}: BrandSectionProps): React.JSX.Element {
  const n = (v: string | null) => v ?? "";

  const [form, setForm] = useState({
    brand_name: n(data.brand_name),
    signature_name: n(data.signature_name),
    signature_role: n(data.signature_role),
    signature_company: n(data.signature_company),
    portfolio_url: n(data.portfolio_url),
    website_url: n(data.website_url),
    calendar_url: n(data.calendar_url),
    default_outreach_tone: data.default_outreach_tone || "profesional",
    default_reply_tone: data.default_reply_tone || "profesional",
  });

  const set =
    <K extends keyof typeof form>(k: K) =>
    (v: (typeof form)[K]) =>
      setForm((prev) => ({ ...prev, [k]: v }));

  const getData = useCallback(
    (): Partial<OperationalSettings> => ({
      brand_name: form.brand_name || null,
      signature_name: form.signature_name || null,
      signature_role: form.signature_role || null,
      signature_company: form.signature_company || null,
      portfolio_url: form.portfolio_url || null,
      website_url: form.website_url || null,
      calendar_url: form.calendar_url || null,
      default_outreach_tone: form.default_outreach_tone || "profesional",
      default_reply_tone: form.default_reply_tone || "profesional",
    }),
    [form]
  );

  const { save, saving } = useSave(getData, onSaved);

  return (
    <div className="space-y-4">
      {/* ══════════════════════════════════════════════════
          2-COL LAYOUT
          LEFT:  Identidad + Tono (stacked)
          RIGHT: Links de contacto (card stretches, content top-aligned)
          ══════════════════════════════════════════════════ */}
      <div className="grid gap-4 lg:grid-cols-2 lg:items-stretch">
        {/* LEFT col — Identidad + Tono de comunicación stacked */}
        <div className="space-y-4">
          <SettingsSectionCard title="Identidad">
            <div className="space-y-5">
              <div className="space-y-3">
                <SectionSubheading>Marca</SectionSubheading>
                <Field label="Nombre comercial">
                  <IdentityInput
                    value={form.brand_name}
                    onChange={set("brand_name")}
                    placeholder="ej: Mateo Dev Studio"
                  />
                </Field>
              </div>

              <div className="space-y-3">
                <SectionSubheading>Firmante</SectionSubheading>
                <div className="grid gap-2 sm:grid-cols-3">
                  <Field label="Nombre">
                    <IdentityInput
                      value={form.signature_name}
                      onChange={set("signature_name")}
                      placeholder="Mateo"
                    />
                  </Field>
                  <Field label="Cargo">
                    <IdentityInput
                      value={form.signature_role}
                      onChange={set("signature_role")}
                      placeholder="Desarrollador Web"
                    />
                  </Field>
                  <Field label="Empresa">
                    <IdentityInput
                      value={form.signature_company}
                      onChange={set("signature_company")}
                      placeholder="Mateo Dev"
                    />
                  </Field>
                </div>
              </div>
            </div>
          </SettingsSectionCard>

          <SettingsSectionCard title="Tono de comunicación">
            <div className="space-y-3">
              <div className="space-y-1.5">
                <SectionSubheading>Outreach</SectionSubheading>
                <ToneChips
                  value={form.default_outreach_tone}
                  onChange={
                    set("default_outreach_tone") as (v: ToneValue) => void
                  }
                />
              </div>
              <div className="space-y-1.5">
                <SectionSubheading>Respuestas</SectionSubheading>
                <ToneChips
                  value={form.default_reply_tone}
                  onChange={set("default_reply_tone") as (v: ToneValue) => void}
                />
              </div>
            </div>
          </SettingsSectionCard>
        </div>

        {/* RIGHT col — Links de contacto */}
        <SettingsSectionCard title="Links de contacto">
          <div className="space-y-3">
            <Field label="Sitio web">
              <IdentityInput
                value={form.website_url}
                onChange={set("website_url")}
                placeholder="https://mateodev.com"
                icon={Globe}
                mono
              />
            </Field>
            <Field label="Calendario">
              <IdentityInput
                value={form.calendar_url}
                onChange={set("calendar_url")}
                placeholder="https://cal.com/mateo"
                icon={CalendarDays}
                mono
              />
            </Field>
            <Field label="Portfolio">
              <IdentityInput
                value={form.portfolio_url}
                onChange={set("portfolio_url")}
                placeholder="https://portfolio.mateodev.com"
                icon={ExternalLink}
                mono
              />
            </Field>
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

"use client";

import { useCallback, useState } from "react";
import { DollarSign, RotateCcw } from "lucide-react";
import { sileo } from "sileo";
import { cn } from "@/lib/utils";
import { SectionFooter, SettingsSectionCard } from "./settings-primitives";
import { updateOperationalSettings } from "@/lib/api/client";
import type { OperationalSettings } from "@/types";

interface PricingSectionProps {
  data: OperationalSettings;
  onSaved: (updated: OperationalSettings) => void;
}

const DEFAULT_MATRIX: Record<string, { min: number; max: number }> = {
  landing: { min: 300, max: 600 },
  institutional_web: { min: 500, max: 1200 },
  catalog: { min: 600, max: 1500 },
  ecommerce: { min: 1500, max: 4000 },
  redesign: { min: 400, max: 1000 },
  automation: { min: 800, max: 3000 },
  branding_web: { min: 1000, max: 2500 },
};

const SCOPE_LABELS: Record<string, string> = {
  landing: "Landing page",
  institutional_web: "Web institucional",
  catalog: "Catálogo",
  ecommerce: "E-commerce",
  redesign: "Rediseño",
  automation: "Automatización / IA",
  branding_web: "Branding + Web",
};

function parseMatrix(raw: string | null): Record<string, { min: number; max: number }> | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Record<string, { min: number; max: number }>;
  } catch {
    return null;
  }
}

export function PricingSection({ data, onSaved }: PricingSectionProps) {
  const [matrix, setMatrix] = useState<Record<string, { min: number; max: number }>>(
    parseMatrix(data.pricing_matrix) || DEFAULT_MATRIX
  );
  const [saving, setSaving] = useState(false);

  const handleChange = useCallback(
    (scope: string, field: "min" | "max", value: string) => {
      const num = parseInt(value, 10);
      if (isNaN(num) || num < 0) return;
      setMatrix((prev) => ({
        ...prev,
        [scope]: { ...prev[scope], [field]: num },
      }));
    },
    []
  );

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await sileo.promise(
        updateOperationalSettings({ pricing_matrix: JSON.stringify(matrix) }),
        {
          loading: { title: "Guardando matriz de precios…" },
          success: { title: "Matriz de precios guardada" },
          error: (err: unknown) => ({
            title: "Error al guardar",
            description: err instanceof Error ? err.message : "Error desconocido",
          }),
        }
      );
      onSaved(updated);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => setMatrix(DEFAULT_MATRIX);

  return (
    <div className="space-y-4">
      <SettingsSectionCard
        title="Matriz de precios"
        description="Rangos de presupuesto estimado por tipo de proyecto (USD). Mote usa estos valores cuando arma propuestas."
        icon={DollarSign}
        action={
          <button
            type="button"
            onClick={handleReset}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Resetear
          </button>
        }
      >
        <div className="overflow-hidden rounded-xl border border-border/60">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                <th className="px-4 py-2 text-left text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Tipo de proyecto
                </th>
                <th className="px-4 py-2 text-left text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Mín (USD)
                </th>
                <th className="px-4 py-2 text-left text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Máx (USD)
                </th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(matrix).map(([scope, range], idx, arr) => (
                <tr
                  key={scope}
                  className={cn(
                    "transition-colors hover:bg-muted/40",
                    idx !== arr.length - 1 && "border-b border-border/60"
                  )}
                >
                  <td className="px-4 py-2 text-xs text-foreground">
                    {SCOPE_LABELS[scope] || scope}
                  </td>
                  <td className="px-4 py-2">
                    <PriceInput
                      value={range.min}
                      onChange={(v) => handleChange(scope, "min", v)}
                    />
                  </td>
                  <td className="px-4 py-2">
                    <PriceInput
                      value={range.max}
                      onChange={(v) => handleChange(scope, "max", v)}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SettingsSectionCard>
      <SectionFooter
        updatedAt={data.updated_at}
        onSave={handleSave}
        saving={saving}
      />
    </div>
  );
}

function PriceInput({
  value,
  onChange,
}: {
  value: number;
  onChange: (v: string) => void;
}) {
  return (
    <input
      type="number"
      min={0}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-24 rounded-lg border border-border bg-muted/40 px-2.5 py-1 font-data text-xs text-foreground outline-none transition-colors focus:border-ring focus:bg-card focus:ring-3 focus:ring-ring/30 dark:bg-input/30"
    />
  );
}

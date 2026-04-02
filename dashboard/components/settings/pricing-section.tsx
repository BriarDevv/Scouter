"use client";

import { useState } from "react";
import { sileo } from "sileo";
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
  catalog: "Catalogo",
  ecommerce: "E-commerce",
  redesign: "Rediseno",
  automation: "Automatizacion / IA",
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

  const handleChange = (scope: string, field: "min" | "max", value: string) => {
    const num = parseInt(value, 10);
    if (isNaN(num) || num < 0) return;
    setMatrix((prev) => ({
      ...prev,
      [scope]: { ...prev[scope], [field]: num },
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await updateOperationalSettings({
        pricing_matrix: JSON.stringify(matrix),
      });
      onSaved(updated);
      sileo.success({ title: "Matriz de precios guardada" });
    } catch (err) {
      sileo.error({
        title: "Error al guardar",
        description: err instanceof Error ? err.message : "Error desconocido",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setMatrix(DEFAULT_MATRIX);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium">Matriz de Precios</h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Rangos de presupuesto estimado por tipo de proyecto (USD)
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleReset}
            className="rounded-lg border border-border px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted transition-colors"
          >
            Resetear
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded-lg bg-foreground text-background px-3 py-1.5 text-xs font-medium hover:bg-foreground/90 transition-colors disabled:opacity-50"
          >
            {saving ? "Guardando..." : "Guardar"}
          </button>
        </div>
      </div>

      <div className="rounded-xl border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/30">
              <th className="text-left px-4 py-2 text-xs font-medium text-muted-foreground">
                Tipo de proyecto
              </th>
              <th className="text-left px-4 py-2 text-xs font-medium text-muted-foreground">
                Min (USD)
              </th>
              <th className="text-left px-4 py-2 text-xs font-medium text-muted-foreground">
                Max (USD)
              </th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(matrix).map(([scope, range]) => (
              <tr key={scope} className="border-b border-border/50 last:border-0">
                <td className="px-4 py-2 text-foreground">
                  {SCOPE_LABELS[scope] || scope}
                </td>
                <td className="px-4 py-2">
                  <input
                    type="number"
                    min={0}
                    value={range.min}
                    onChange={(e) => handleChange(scope, "min", e.target.value)}
                    className="w-24 rounded-md border border-border bg-background px-2 py-1 text-sm"
                  />
                </td>
                <td className="px-4 py-2">
                  <input
                    type="number"
                    min={0}
                    value={range.max}
                    onChange={(e) => handleChange(scope, "max", e.target.value)}
                    className="w-24 rounded-md border border-border bg-background px-2 py-1 text-sm"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

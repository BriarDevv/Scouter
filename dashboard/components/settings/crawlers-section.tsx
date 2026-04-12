"use client";

import { useEffect, useState } from "react";
import {
  ChevronDown,
  Key,
  Search,
  Trash2,
} from "lucide-react";
import { sileo } from "sileo";
import { cn } from "@/lib/utils";
import { apiFetch } from "@/lib/api/client";
import {
  FieldRow,
  PasswordInput,
  SaveButton,
  Select,
  SettingsSectionCard,
  StatusPill,
} from "./settings-primitives";

// ─── Types ───────────────────────────────────────────────────────────

interface ApiKeyStatus {
  configured: boolean;
  masked: string | null;
  managed_by: "db" | "env" | "none" | string;
  source: "db" | "env" | null;
  mutable_via_api: boolean;
  updated_at: string | null;
  instructions: string;
}

interface Territory {
  id: string;
  name: string;
  cities: string[];
  color: string;
  is_active: boolean;
}

interface CrawlProgress {
  status: "idle" | "running" | "done" | "error";
  territory?: string;
  total_cities?: number;
  current_city_idx?: number;
  current_city?: string;
  leads_found?: number;
  leads_created?: number;
  leads_skipped?: number;
  error?: string;
}

const DEFAULT_CATEGORIES = [
  "restaurante", "peluqueria", "gimnasio", "clinica",
  "estudio contable", "inmobiliaria", "taller mecanico",
  "veterinaria", "floreria", "lavadero de autos",
  "panaderia", "ferreteria", "optica", "libreria",
  "hotel", "hostel", "bar", "cafeteria",
];

// ─── Component ───────────────────────────────────────────────────────

export function CrawlersSection() {
  const [apiKeyStatus, setApiKeyStatus] = useState<ApiKeyStatus | null>(null);
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [savingApiKey, setSavingApiKey] = useState(false);

  const [territories, setTerritories] = useState<Territory[]>([]);
  const [selectedTerritoryId, setSelectedTerritoryId] = useState<string>("");
  const [selectedCats, setSelectedCats] = useState<string[]>([]);
  const [progress] = useState<CrawlProgress>({ status: "idle" });

  useEffect(() => {
    apiFetch<ApiKeyStatus>("/crawl/api-key-status")
      .then(setApiKeyStatus)
      .catch(() => {});

    apiFetch<Territory[]>("/territories")
      .then((data) => {
        setTerritories(data);
        if (data.length > 0) setSelectedTerritoryId(data[0].id);
      })
      .catch(() => {});
  }, []);

  const handleSaveApiKey = async () => {
    const trimmed = apiKeyInput.trim();
    if (!trimmed) return;
    setSavingApiKey(true);
    try {
      const updated = await sileo.promise(
        apiFetch<ApiKeyStatus>("/crawl/api-key", {
          method: "PATCH",
          body: JSON.stringify({ api_key: trimmed }),
        }),
        {
          loading: { title: "Guardando API key…" },
          success: { title: "Google Maps API key guardada" },
          error: (err: unknown) => ({
            title: "No se pudo guardar la API key",
            description: err instanceof Error ? err.message : "Error desconocido",
          }),
        }
      );
      setApiKeyStatus(updated);
      setApiKeyInput("");
    } finally {
      setSavingApiKey(false);
    }
  };

  const handleClearApiKey = async () => {
    setSavingApiKey(true);
    try {
      const updated = await sileo.promise(
        apiFetch<ApiKeyStatus>("/crawl/api-key", { method: "DELETE" }),
        {
          loading: { title: "Limpiando API key…" },
          success: { title: "API key eliminada de la DB" },
          error: (err: unknown) => ({
            title: "No se pudo eliminar",
            description: err instanceof Error ? err.message : "Error desconocido",
          }),
        }
      );
      setApiKeyStatus(updated);
    } finally {
      setSavingApiKey(false);
    }
  };

  const toggleCat = (cat: string) => {
    setSelectedCats((prev) =>
      prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat]
    );
  };

  const selectedTerritory = territories.find((t) => t.id === selectedTerritoryId);
  const isRunning = progress.status === "running";

  return (
    <div className="space-y-6">
      {/* ── Google Maps API key ──────────────────────────────────── */}
      <SettingsSectionCard
        title="Google Maps API"
        description="Se guarda encriptada en la base. GOOGLE_MAPS_API_KEY del .env sigue como fallback."
        icon={Key}
        action={
          <StatusPill
            label={apiKeyStatus?.configured ? "Configurada" : "No configurada"}
            tone={apiKeyStatus?.configured ? "positive" : "warning"}
          />
        }
      >
        <div className="grid gap-6 lg:grid-cols-[1fr,1fr]">
          <div className="space-y-3">
            <FieldRow
              label="API Key"
              hint={
                apiKeyStatus?.source === "db"
                  ? "Origen activo: DB (guardada desde este panel)"
                  : apiKeyStatus?.source === "env"
                    ? "Origen activo: GOOGLE_MAPS_API_KEY del .env"
                    : "Sin origen configurado"
              }
            >
              <PasswordInput
                value={apiKeyInput}
                onChange={setApiKeyInput}
                placeholder="AIzaSy..."
                alreadySet={apiKeyStatus?.configured}
              />
            </FieldRow>

          </div>

          <div className="rounded-xl border border-border/60 bg-muted/30 p-4 text-[11px] leading-relaxed text-muted-foreground">
            Habilitá <span className="font-data text-foreground/80">Places API (New)</span>{" "}
            en Google Cloud Console y restringí la key a esa API. Desde marzo 2025 el
            free tier es <strong className="text-foreground">10.000 requests/mes</strong>{" "}
            por SKU (ya no el crédito universal de $200). El crawler pide rating,
            teléfono y horarios, así que probablemente factura como{" "}
            <span className="font-data text-foreground/80">Text Search Pro</span> (~$32
            por 1.000 requests después del cap gratuito). Verificá el SKU en Cloud
            Billing.
          </div>
        </div>

        <div className="mt-4 flex items-center gap-2">
          <SaveButton
            onClick={handleSaveApiKey}
            saving={savingApiKey}
            disabled={!apiKeyInput.trim()}
          />
          {apiKeyStatus?.source === "db" && (
            <button
              type="button"
              onClick={handleClearApiKey}
              disabled={savingApiKey}
              title="Borra la key de la DB (el fallback de .env sigue activo si existe)"
              className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-50"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Limpiar DB
            </button>
          )}
        </div>
      </SettingsSectionCard>

      {/* ── Crawl by territory ───────────────────────────────────── */}
      <SettingsSectionCard
        title="Buscar leads por territorio"
        description="Selecciona un territorio y el crawler busca negocios en todas sus ciudades."
        icon={Search}
      >
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="space-y-4">
            <FieldRow label="Territorio" hint="Cada territorio define su listado de ciudades">
              <div className="relative">
                <Select
                  value={selectedTerritoryId}
                  onChange={setSelectedTerritoryId}
                  disabled={isRunning}
                >
                  {territories.length === 0 && (
                    <option value="">No hay territorios configurados</option>
                  )}
                  {territories.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name} ({t.cities.length} ciudades)
                    </option>
                  ))}
                </Select>
                <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              </div>
            </FieldRow>

            {selectedTerritory && selectedTerritory.cities.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {selectedTerritory.cities.map((c) => (
                  <span
                    key={c}
                    className="rounded-md px-2 py-0.5 text-[10px] font-medium"
                    style={{
                      backgroundColor: `${selectedTerritory.color}18`,
                      color: selectedTerritory.color,
                    }}
                  >
                    {c}
                  </span>
                ))}
              </div>
            )}

          </div>

          <div className="space-y-4">
            <FieldRow label="Rubros">
            <div className="flex max-h-48 flex-wrap gap-1.5 overflow-y-auto rounded-lg border border-border/40 bg-muted/20 p-2">
              {DEFAULT_CATEGORIES.map((cat) => {
                const active = selectedCats.includes(cat);
                return (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => toggleCat(cat)}
                    disabled={isRunning}
                    className={cn(
                      "rounded-md px-2.5 py-1 text-xs font-medium transition-colors disabled:opacity-50",
                      active
                        ? "bg-foreground text-background"
                        : "bg-card text-muted-foreground hover:bg-muted hover:text-foreground"
                    )}
                  >
                    {cat}
                  </button>
                );
              })}
            </div>
          </FieldRow>
          </div>
        </div>

      </SettingsSectionCard>
    </div>
  );
}

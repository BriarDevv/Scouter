"use client";

import { useCallback, useState, useEffect } from "react";
import { useVisibleInterval } from "@/lib/hooks/use-visible-interval";
import {
  Key, Search, Loader2, CheckCircle2, XCircle,
  Power, PowerOff, ChevronDown,
} from "lucide-react";
import { sileo } from "sileo";
import { SettingsSectionCard, FieldRow } from "./settings-primitives";
import { apiFetch } from "@/lib/api/client";

// ─── Types ───────────────────────────────────────────────────────────

interface ApiKeyStatus {
  configured: boolean;
  masked: string | null;
  managed_by: string;
  mutable_via_api: boolean;
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

  const [territories, setTerritories] = useState<Territory[]>([]);
  const [selectedTerritoryId, setSelectedTerritoryId] = useState<string>("");
  const [onlyNoWebsite, setOnlyNoWebsite] = useState(false);
  const [selectedCats, setSelectedCats] = useState<string[]>([]);
  const [progress, setProgress] = useState<CrawlProgress>({ status: "idle" });
  const [starting, setStarting] = useState(false);

  // Fetch initial data
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

  // Poll progress when running
  const pollCrawlStatus = useCallback(async () => {
    if (progress.status !== "running" || !selectedTerritoryId) return;
    try {
      const data = await apiFetch<CrawlProgress>(`/crawl/territory/${selectedTerritoryId}/status`);
      setProgress(data);
      if (data.status === "done") {
        sileo.success({
          title: `Crawl completado: ${data.leads_created ?? 0} leads nuevos`,
        });
      }
      if (data.status === "error") {
        sileo.error({ title: data.error ?? "Error en el crawl" });
      }
    } catch (err) { console.error("crawl_status_poll_failed", err); }
  }, [progress.status, selectedTerritoryId]);

  useVisibleInterval(pollCrawlStatus, 2000);

  // Also check on territory change if there's a running crawl
  useEffect(() => {
    if (!selectedTerritoryId) return;
    apiFetch<CrawlProgress>(`/crawl/territory/${selectedTerritoryId}/status`)
      .then((data) => setProgress(data))
      .catch(() => setProgress({ status: "idle" }));
  }, [selectedTerritoryId]);

  const handleStart = async () => {
    if (!selectedTerritoryId) return;
    setStarting(true);
    try {
      const data = await apiFetch<Record<string, unknown>>("/crawl/territory", {
        method: "POST",
        body: JSON.stringify({
          territory_id: selectedTerritoryId,
          categories: selectedCats.length > 0 ? selectedCats : null,
          only_without_website: onlyNoWebsite,
        }),
      });
      if (data.ok) {
        setProgress({ status: "running", territory: data.message as string });
        sileo.success({ title: data.message as string });
      } else {
        sileo.error({ title: (data.message as string) ?? "Error al iniciar crawl" });
        if (data.progress) setProgress(data.progress as CrawlProgress);
      }
    } catch (err) {
      console.error("crawl_start_failed", err);
      sileo.error({ title: "Error de conexion" });
    } finally {
      setStarting(false);
    }
  };

  const handleStop = async () => {
    if (!selectedTerritoryId) return;
    await apiFetch(`/crawl/territory/${selectedTerritoryId}/stop`, { method: "POST" });
    setProgress({ status: "idle" });
    sileo.success({ title: "Crawl detenido" });
  };

  const toggleCat = (cat: string) => {
    setSelectedCats((prev) =>
      prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat]
    );
  };

  const selectedTerritory = territories.find((t) => t.id === selectedTerritoryId);
  const isRunning = progress.status === "running";
  const isDone = progress.status === "done";
  const isError = progress.status === "error";

  return (
    <div className="space-y-6">
      {/* API Key */}
      <SettingsSectionCard
        title="Google Maps API"
        description="La API Key de Google Maps es configuración de deploy. Este panel solo muestra el estado actual."
        icon={Key}
      >
        <div className="grid gap-0 lg:grid-cols-2 lg:gap-x-8">
          <div>
            <FieldRow label="Origen" hint="Se administra fuera de la aplicación">
              <div className="rounded-xl border border-border bg-muted px-3 py-2 text-sm text-foreground">
                Variable de entorno: <span className="font-mono">GOOGLE_MAPS_API_KEY</span>
              </div>
            </FieldRow>
            {apiKeyStatus?.configured && apiKeyStatus.masked && (
              <p className="mt-1 text-[10px] text-muted-foreground">
                Actual: {apiKeyStatus.masked}
              </p>
            )}
            <p className="mt-3 text-xs text-muted-foreground">
              {apiKeyStatus?.instructions ??
                "Definí GOOGLE_MAPS_API_KEY en el entorno y reiniciá la API/worker."}
            </p>
          </div>
          <div className="flex items-end pb-5">
            <span
              className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${
                apiKeyStatus?.configured
                  ? "bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700"
                  : "bg-amber-50 dark:bg-amber-950/30 text-amber-700"
              }`}
            >
              {apiKeyStatus?.configured ? (
                <><CheckCircle2 className="h-3 w-3" /> Configurada</>
              ) : (
                <><XCircle className="h-3 w-3" /> No configurada</>
              )}
            </span>
          </div>
        </div>
      </SettingsSectionCard>

      {/* Crawl by territory */}
      <SettingsSectionCard
        title="Buscar leads por territorio"
        description="Selecciona un territorio y el crawler busca negocios en todas sus ciudades."
        icon={Search}
      >
        <div className="grid gap-0 lg:grid-cols-2 lg:gap-x-8">
          <div>
            {/* Territory selector */}
            <FieldRow label="Territorio" hint="Cada territorio tiene un listado de ciudades">
              <div className="relative">
                <select
                  value={selectedTerritoryId}
                  onChange={(e) => setSelectedTerritoryId(e.target.value)}
                  disabled={isRunning}
                  className="w-full appearance-none rounded-xl border border-border bg-muted px-3 py-2 pr-8 text-sm text-foreground outline-none transition focus:border-border focus:bg-card disabled:opacity-50"
                >
                  {territories.length === 0 && (
                    <option value="">No hay territorios configurados</option>
                  )}
                  {territories.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name} ({t.cities.length} ciudades)
                    </option>
                  ))}
                </select>
                <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              </div>
            </FieldRow>

            {/* Cities preview */}
            {selectedTerritory && (
              <div className="mb-4 flex flex-wrap gap-1">
                {selectedTerritory.cities.map((c) => (
                  <span
                    key={c}
                    className="rounded-lg px-2 py-0.5 text-[10px] font-medium"
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

            {/* Filters */}
            <FieldRow label="Solo sin website" hint="Negocios sin pagina web (leads de alto valor)">
              <label className="flex cursor-pointer items-center gap-2">
                <input
                  type="checkbox"
                  checked={onlyNoWebsite}
                  onChange={(e) => setOnlyNoWebsite(e.target.checked)}
                  disabled={isRunning}
                  className="h-4 w-4 rounded border-border"
                />
                <span className="text-sm text-foreground">
                  {onlyNoWebsite ? "Solo sin website" : "Todos los negocios"}
                </span>
              </label>
            </FieldRow>
          </div>

          {/* Categories */}
          <div>
            <FieldRow label="Rubros" hint="Selecciona rubros (vacio = todos)">
              <div className="flex flex-wrap gap-1.5 max-h-44 overflow-y-auto">
                {DEFAULT_CATEGORIES.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => toggleCat(cat)}
                    disabled={isRunning}
                    className={`rounded-lg px-2.5 py-1 text-[11px] font-medium transition-colors disabled:opacity-50 ${
                      selectedCats.includes(cat)
                        ? "bg-foreground text-background"
                        : "bg-muted text-muted-foreground hover:bg-muted/80"
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </FieldRow>
          </div>
        </div>

        {/* Toggle button */}
        <div className="mt-4 flex items-center gap-3">
          {!isRunning ? (
            <button
              onClick={handleStart}
              disabled={starting || !selectedTerritoryId || !apiKeyStatus?.configured}
              className="flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 transition-colors disabled:opacity-40"
            >
              {starting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Power className="h-4 w-4" />
              )}
              {starting ? "Iniciando..." : "Iniciar crawl"}
            </button>
          ) : (
            <button
              onClick={handleStop}
              className="flex items-center gap-2 rounded-xl bg-red-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-red-700 transition-colors"
            >
              <PowerOff className="h-4 w-4" />
              Detener crawl
            </button>
          )}

          {!apiKeyStatus?.configured && (
            <p className="text-[10px] text-amber-600">
              Configura la API Key arriba para poder buscar.
            </p>
          )}
        </div>

        {/* Progress */}
        {isRunning && (
          <div className="mt-4 rounded-xl border border-border bg-muted dark:bg-muted p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin text-foreground" />
                <p className="text-sm font-semibold text-foreground">
                  Crawling {progress.territory ?? "..."}
                </p>
              </div>
              <span className="text-[10px] text-foreground font-mono">
                {progress.current_city_idx ?? 0}/{progress.total_cities ?? 0} ciudades
              </span>
            </div>

            {/* Progress bar */}
            <div className="h-2 rounded-full bg-muted-foreground/20 overflow-hidden">
              <div
                className="h-full rounded-full bg-foreground transition-[width] duration-500"
                style={{
                  width: `${progress.total_cities ? ((progress.current_city_idx ?? 0) / progress.total_cities) * 100 : 0}%`,
                }}
              />
            </div>

            <div className="flex items-center justify-between text-[10px] text-foreground">
              <span>
                Buscando en: <strong>{progress.current_city ?? "..."}</strong>
              </span>
              <span>
                {progress.leads_found ?? 0} encontrados · {progress.leads_created ?? 0} nuevos
              </span>
            </div>
          </div>
        )}

        {/* Done */}
        {isDone && (
          <div className="mt-4 rounded-xl border border-emerald-500/20 bg-emerald-50 dark:bg-emerald-950/20 p-4 space-y-2">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-600" />
              <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-300">
                Crawl completado
              </p>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <StatBox label="Encontrados" value={progress.leads_found ?? 0} />
              <StatBox label="Creados" value={progress.leads_created ?? 0} highlight />
              <StatBox label="Duplicados" value={progress.leads_skipped ?? 0} />
            </div>
          </div>
        )}

        {/* Error */}
        {isError && (
          <div className="mt-4 rounded-xl border border-red-500/20 bg-red-50 dark:bg-red-950/20 p-3">
            <p className="text-xs text-red-600 flex items-center gap-1.5">
              <XCircle className="h-3.5 w-3.5" />
              {progress.error ?? "Error desconocido"}
            </p>
          </div>
        )}
      </SettingsSectionCard>
    </div>
  );
}

function StatBox({ label, value, highlight }: { label: string; value: number; highlight?: boolean }) {
  return (
    <div className="rounded-lg bg-card border border-border p-2.5 text-center">
      <p className={`text-lg font-bold ${highlight ? "text-emerald-600" : "text-foreground"}`}>
        {value}
      </p>
      <p className="text-[10px] text-muted-foreground">{label}</p>
    </div>
  );
}

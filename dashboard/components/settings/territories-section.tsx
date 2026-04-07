"use client";

import { useCallback, useEffect, useState } from "react";
import { MapPin, Plus, Pencil, Trash2, Loader2 } from "lucide-react";
import { sileo } from "sileo";
import {
  SettingsSectionCard,
  FieldRow,
  TextInput,
  SaveButton,
} from "./settings-primitives";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  getTerritories,
  createTerritory,
  updateTerritory,
  deleteTerritory,
} from "@/lib/api/client";
import type { TerritoryWithStats } from "@/types";
import { CITY_COORDS } from "@/data/cities-ar";

const PRESET_COLORS = [
  "#8b5cf6", "#3b82f6", "#22c55e", "#eab308", "#ef4444",
  "#ec4899", "#14b8a6", "#f97316", "#6366f1", "#06b6d4",
];

const ALL_CITIES = Object.keys(CITY_COORDS).sort();

interface TerritoryFormData {
  name: string;
  description: string;
  color: string;
  cities: string[];
  is_active: boolean;
}

const EMPTY_FORM: TerritoryFormData = {
  name: "",
  description: "",
  color: PRESET_COLORS[0],
  cities: [],
  is_active: true,
};

export function TerritoriesSection() {
  const [territories, setTerritories] = useState<TerritoryWithStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<TerritoryFormData>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [citySearch, setCitySearch] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getTerritories();
      setTerritories(data);
    } catch (err) {
      console.error("territories_fetch_failed", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function startCreate() {
    setCreating(true);
    setEditing(null);
    setForm(EMPTY_FORM);
    setCitySearch("");
  }

  function startEdit(t: TerritoryWithStats) {
    setEditing(t.id);
    setCreating(false);
    setForm({
      name: t.name,
      description: t.description || "",
      color: t.color,
      cities: [...t.cities],
      is_active: t.is_active,
    });
    setCitySearch("");
  }

  function cancel() {
    setCreating(false);
    setEditing(null);
    setForm(EMPTY_FORM);
  }

  async function handleSave() {
    setSaving(true);
    try {
      if (creating) {
        await sileo.promise(createTerritory(form), {
          loading: { title: "Creando territorio..." },
          success: { title: "Territorio creado" },
          error: (err: unknown) => ({
            title: "Error",
            description: err instanceof Error ? err.message : "No se pudo crear.",
          }),
        });
      } else if (editing) {
        await sileo.promise(updateTerritory(editing, form), {
          loading: { title: "Guardando territorio..." },
          success: { title: "Territorio actualizado" },
          error: (err: unknown) => ({
            title: "Error",
            description: err instanceof Error ? err.message : "No se pudo guardar.",
          }),
        });
      }
      cancel();
      await load();
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: string) {
    await sileo.promise(deleteTerritory(id), {
      loading: { title: "Eliminando territorio..." },
      success: { title: "Territorio eliminado" },
      error: (err: unknown) => ({
        title: "Error",
        description: err instanceof Error ? err.message : "No se pudo eliminar.",
      }),
    });
    await load();
  }

  function toggleCity(city: string) {
    setForm((prev) => ({
      ...prev,
      cities: prev.cities.includes(city)
        ? prev.cities.filter((c) => c !== city)
        : [...prev.cities, city],
    }));
  }

  const filteredCities = ALL_CITIES.filter((c) =>
    c.toLowerCase().includes(citySearch.toLowerCase())
  );

  const isEditorOpen = creating || editing !== null;

  return (
    <div className="space-y-6">
      <SettingsSectionCard
        title="Territorios"
        description="Agrupa ciudades en territorios para analizar el rendimiento geografico de tus leads."
        icon={MapPin}
      >
        {loading ? (
          <div className="flex items-center gap-2 py-4 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Cargando territorios...
          </div>
        ) : territories.length === 0 && !isEditorOpen ? (
          <div className="rounded-xl bg-muted p-6 text-center text-sm text-muted-foreground">
            No hay territorios configurados. Crea el primero para empezar a agrupar ciudades.
          </div>
        ) : (
          <div className="space-y-2">
            {territories.map((t) => (
              <div
                key={t.id}
                className={cn(
                  "flex items-center gap-3 rounded-xl border border-border bg-card px-4 py-3 transition-colors",
                  editing === t.id && "ring-2 ring-violet-500/30"
                )}
              >
                <span
                  className="h-4 w-4 rounded-full shrink-0"
                  style={{ backgroundColor: t.color }}
                />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium font-heading text-foreground">{t.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {t.cities.length} ciudad{t.cities.length !== 1 ? "es" : ""} &middot; {t.lead_count} leads &middot; Score: {t.avg_score.toFixed(1)}
                  </p>
                </div>
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => startEdit(t)}
                    disabled={isEditorOpen && editing !== t.id}
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => void handleDelete(t.id)}
                    disabled={isEditorOpen}
                  >
                    <Trash2 className="h-3.5 w-3.5 text-red-500" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        {!isEditorOpen && (
          <div className="mt-4">
            <Button variant="outline" size="sm" className="rounded-xl" onClick={startCreate}>
              <Plus className="mr-1.5 h-3.5 w-3.5" />
              Nuevo territorio
            </Button>
          </div>
        )}

        {isEditorOpen && (
          <div className="mt-4 rounded-xl border border-border bg-muted/30 p-4 space-y-4">
            <h4 className="text-sm font-semibold font-heading text-foreground">
              {creating ? "Nuevo territorio" : "Editar territorio"}
            </h4>
            <div className="grid gap-4 sm:grid-cols-2">
              <FieldRow label="Nombre" hint="Nombre unico del territorio">
                <TextInput
                  value={form.name}
                  onChange={(v) => setForm((p) => ({ ...p, name: v }))}
                  placeholder="Ej: CABA, GBA Norte"
                />
              </FieldRow>
              <FieldRow label="Descripcion" hint="Descripcion opcional">
                <TextInput
                  value={form.description}
                  onChange={(v) => setForm((p) => ({ ...p, description: v }))}
                  placeholder="Zona metropolitana norte..."
                />
              </FieldRow>
            </div>
            <FieldRow label="Color" hint="Color del territorio en el mapa">
              <div className="flex flex-wrap gap-2">
                {PRESET_COLORS.map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setForm((p) => ({ ...p, color: c }))}
                    className={cn(
                      "h-7 w-7 rounded-lg border-2 transition-all",
                      form.color === c ? "border-foreground scale-110" : "border-transparent"
                    )}
                    style={{ backgroundColor: c }}
                  />
                ))}
              </div>
            </FieldRow>
            <FieldRow label="Ciudades" hint="Selecciona las ciudades de este territorio">
              <div className="space-y-2">
                <TextInput value={citySearch} onChange={setCitySearch} placeholder="Buscar ciudad..." />
                {form.cities.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {form.cities.map((c) => (
                      <button
                        key={c}
                        type="button"
                        onClick={() => toggleCity(c)}
                        className="inline-flex items-center gap-1 rounded-full bg-violet-50 dark:bg-violet-950/40 px-2.5 py-1 text-xs font-medium text-violet-700 dark:text-violet-300 hover:bg-violet-100 dark:hover:bg-violet-950/60 transition-colors"
                      >
                        {c} <span className="text-violet-400">&times;</span>
                      </button>
                    ))}
                  </div>
                )}
                <div className="max-h-40 overflow-y-auto rounded-lg border border-border bg-card p-1">
                  {filteredCities.slice(0, 50).map((city) => (
                    <button
                      key={city}
                      type="button"
                      onClick={() => toggleCity(city)}
                      className={cn(
                        "flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-xs transition-colors",
                        form.cities.includes(city)
                          ? "bg-violet-50 dark:bg-violet-950/40 text-violet-700 dark:text-violet-300"
                          : "text-foreground hover:bg-muted"
                      )}
                    >
                      <span className={cn(
                        "h-3 w-3 rounded-sm border",
                        form.cities.includes(city) ? "bg-violet-600 border-violet-600" : "border-border"
                      )} />
                      {city}
                    </button>
                  ))}
                </div>
              </div>
            </FieldRow>
            <div className="flex items-center gap-2 justify-end">
              <Button variant="outline" size="sm" className="rounded-xl" onClick={cancel}>Cancelar</Button>
              <SaveButton onClick={handleSave} saving={saving} />
            </div>
          </div>
        )}
      </SettingsSectionCard>
    </div>
  );
}

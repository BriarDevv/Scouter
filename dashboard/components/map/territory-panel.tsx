"use client";

import { useState } from "react";
import {
  Plus,
  Pencil,
  Trash2,
  X,
  Check,
  MapPin,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { TerritoryWithStats } from "@/types";
import { CITY_COORDS } from "@/data/cities-ar";

interface TerritoryPanelProps {
  territories: TerritoryWithStats[];
  onSave: (data: {
    name: string;
    description: string;
    color: string;
    cities: string[];
    is_active: boolean;
  }) => Promise<void>;
  onUpdate: (
    id: string,
    data: {
      name?: string;
      description?: string;
      color?: string;
      cities?: string[];
      is_active?: boolean;
    }
  ) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}

const AVAILABLE_CITIES = Object.keys(CITY_COORDS).sort();

const DEFAULT_COLORS = [
  "#6366f1",
  "#ec4899",
  "#f97316",
  "#22c55e",
  "#06b6d4",
  "#8b5cf6",
  "#ef4444",
  "#eab308",
];

interface FormState {
  name: string;
  description: string;
  color: string;
  cities: string[];
  is_active: boolean;
}

const EMPTY_FORM: FormState = {
  name: "",
  description: "",
  color: "#6366f1",
  cities: [],
  is_active: true,
};

export function TerritoryPanel({
  territories,
  onSave,
  onUpdate,
  onDelete,
}: TerritoryPanelProps) {
  const [editing, setEditing] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [citySearch, setCitySearch] = useState("");
  const [showCities, setShowCities] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(true);

  function startCreate() {
    setEditing(null);
    setForm(EMPTY_FORM);
    setCreating(true);
    setCitySearch("");
  }

  function startEdit(territory: TerritoryWithStats) {
    setCreating(false);
    setEditing(territory.id);
    setForm({
      name: territory.name,
      description: territory.description ?? "",
      color: territory.color,
      cities: [...territory.cities],
      is_active: territory.is_active,
    });
    setCitySearch("");
  }

  function cancel() {
    setCreating(false);
    setEditing(null);
    setForm(EMPTY_FORM);
    setCitySearch("");
    setShowCities(false);
  }

  async function handleSave() {
    if (!form.name.trim()) return;
    if (creating) {
      await onSave(form);
    } else if (editing) {
      await onUpdate(editing, form);
    }
    cancel();
  }

  function toggleCity(city: string) {
    setForm((prev) => ({
      ...prev,
      cities: prev.cities.includes(city)
        ? prev.cities.filter((c) => c !== city)
        : [...prev.cities, city],
    }));
  }

  const filteredCities = AVAILABLE_CITIES.filter((c) =>
    c.toLowerCase().includes(citySearch.toLowerCase())
  );

  const isFormOpen = creating || editing !== null;

  return (
    <div className="absolute left-3 bottom-3 z-[1000] w-80">
      <div className="rounded-xl border border-border bg-card shadow-lg overflow-hidden">
        {/* Header */}
        <button
          onClick={() => setExpanded((p) => !p)}
          className="flex w-full items-center justify-between px-4 py-3 hover:bg-muted/50 transition-colors"
        >
          <div className="flex items-center gap-2">
            <MapPin className="h-4 w-4 text-foreground" />
            <span className="font-heading text-sm font-semibold text-foreground">
              Territorios ({territories.length})
            </span>
          </div>
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          )}
        </button>

        {expanded && (
          <div className="max-h-[420px] overflow-y-auto border-t border-border">
            {/* Territory list */}
            {territories.length > 0 && (
              <ul className="divide-y divide-border">
                {territories.map((t) => (
                  <li key={t.id} className="px-4 py-2.5">
                    {editing === t.id ? null : (
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 min-w-0">
                          <span
                            className="inline-block h-3 w-3 rounded-full flex-shrink-0"
                            style={{ backgroundColor: t.color }}
                          />
                          <div className="min-w-0">
                            <p className="truncate text-sm font-medium text-foreground">
                              {t.name}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {t.lead_count} leads &middot; Score {t.avg_score.toFixed(1)} &middot;{" "}
                              {t.cities.length} ciudades
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-1 ml-2">
                          <button
                            onClick={() => startEdit(t)}
                            className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                            title="Editar"
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </button>
                          {confirmDelete === t.id ? (
                            <div className="flex items-center gap-1">
                              <button
                                onClick={async () => {
                                  await onDelete(t.id);
                                  setConfirmDelete(null);
                                }}
                                className="rounded p-1 text-red-500 hover:bg-red-50 dark:hover:bg-red-950/40 transition-colors"
                                title="Confirmar"
                              >
                                <Check className="h-3.5 w-3.5" />
                              </button>
                              <button
                                onClick={() => setConfirmDelete(null)}
                                className="rounded p-1 text-muted-foreground hover:text-foreground transition-colors"
                                title="Cancelar"
                              >
                                <X className="h-3.5 w-3.5" />
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={() => setConfirmDelete(t.id)}
                              className="rounded p-1 text-muted-foreground hover:text-red-500 hover:bg-muted transition-colors"
                              title="Eliminar"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          )}
                        </div>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            )}

            {territories.length === 0 && !isFormOpen && (
              <p className="px-4 py-6 text-center text-sm text-muted-foreground">
                No hay territorios definidos
              </p>
            )}

            {/* Create/Edit form */}
            {isFormOpen && (
              <div className="border-t border-border px-4 py-3 space-y-3">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  {creating ? "Nuevo territorio" : "Editar territorio"}
                </p>

                {/* Name */}
                <input
                  type="text"
                  placeholder="Nombre del territorio"
                  value={form.name}
                  onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
                  className="w-full rounded-lg border border-border bg-muted/50 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring/50 focus:border-ring"
                />

                {/* Description */}
                <input
                  type="text"
                  placeholder="Descripcion (opcional)"
                  value={form.description}
                  onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
                  className="w-full rounded-lg border border-border bg-muted/50 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring/50 focus:border-ring"
                />

                {/* Color */}
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Color</label>
                  <div className="flex items-center gap-1.5">
                    {DEFAULT_COLORS.map((c) => (
                      <button
                        key={c}
                        onClick={() => setForm((prev) => ({ ...prev, color: c }))}
                        className={cn(
                          "h-6 w-6 rounded-full border-2 transition-all",
                          form.color === c
                            ? "border-foreground scale-110"
                            : "border-transparent hover:scale-105"
                        )}
                        style={{ backgroundColor: c }}
                      />
                    ))}
                    <input
                      type="text"
                      value={form.color}
                      onChange={(e) => setForm((prev) => ({ ...prev, color: e.target.value }))}
                      className="ml-2 w-20 rounded border border-border bg-muted/50 px-2 py-0.5 text-xs font-mono"
                      maxLength={7}
                    />
                  </div>
                </div>

                {/* Cities multiselect */}
                <div>
                  <button
                    onClick={() => setShowCities((p) => !p)}
                    className="flex w-full items-center justify-between rounded-lg border border-border bg-muted/50 px-3 py-1.5 text-sm text-left"
                  >
                    <span>
                      {form.cities.length > 0
                        ? `${form.cities.length} ciudades seleccionadas`
                        : "Seleccionar ciudades"}
                    </span>
                    <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                  </button>

                  {showCities && (
                    <div className="mt-1 rounded-lg border border-border bg-card max-h-40 overflow-y-auto">
                      <div className="sticky top-0 bg-card px-2 py-1.5 border-b border-border">
                        <input
                          type="text"
                          placeholder="Buscar..."
                          value={citySearch}
                          onChange={(e) => setCitySearch(e.target.value)}
                          className="w-full rounded border border-border bg-muted/50 px-2 py-1 text-xs focus:outline-none"
                        />
                      </div>
                      {filteredCities.map((city) => (
                        <label
                          key={city}
                          className="flex items-center gap-2 px-3 py-1 text-xs hover:bg-muted/50 cursor-pointer"
                        >
                          <input
                            type="checkbox"
                            checked={form.cities.includes(city)}
                            onChange={() => toggleCity(city)}
                            className="rounded border-border"
                          />
                          {city}
                        </label>
                      ))}
                    </div>
                  )}

                  {/* Selected chips */}
                  {form.cities.length > 0 && (
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      {form.cities.slice(0, 8).map((city) => (
                        <span
                          key={city}
                          className="inline-flex items-center gap-1 rounded-full bg-muted dark:bg-muted px-2 py-0.5 text-[10px] font-medium text-foreground dark:text-foreground"
                        >
                          {city}
                          <button
                            onClick={() => toggleCity(city)}
                            className="hover:text-red-500"
                          >
                            <X className="h-2.5 w-2.5" />
                          </button>
                        </span>
                      ))}
                      {form.cities.length > 8 && (
                        <span className="text-[10px] text-muted-foreground py-0.5">
                          +{form.cities.length - 8} mas
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* Active toggle */}
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={form.is_active}
                    onChange={(e) =>
                      setForm((prev) => ({ ...prev, is_active: e.target.checked }))
                    }
                    className="rounded border-border"
                  />
                  <span className="text-muted-foreground">Activo</span>
                </label>

                {/* Actions */}
                <div className="flex items-center gap-2 pt-1">
                  <button
                    onClick={handleSave}
                    disabled={!form.name.trim()}
                    className="flex-1 rounded-lg bg-foreground px-3 py-1.5 text-sm font-medium text-background hover:bg-foreground/80 disabled:opacity-50 transition-colors"
                  >
                    {creating ? "Crear" : "Guardar"}
                  </button>
                  <button
                    onClick={cancel}
                    className="rounded-lg border border-border px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted transition-colors"
                  >
                    Cancelar
                  </button>
                </div>
              </div>
            )}

            {/* Add button */}
            {!isFormOpen && (
              <div className="border-t border-border px-4 py-2">
                <button
                  onClick={startCreate}
                  className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-dashed border-border px-3 py-2 text-sm text-muted-foreground hover:border-foreground/40 hover:text-foreground dark:hover:text-foreground transition-colors"
                >
                  <Plus className="h-3.5 w-3.5" />
                  Agregar territorio
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

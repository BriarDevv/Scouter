"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import type { GeoSummaryCity } from "@/types";

interface MapSidebarProps {
  cities: GeoSummaryCity[];
  open: boolean;
  onToggle: () => void;
}

export function MapSidebar({ cities, open, onToggle }: MapSidebarProps) {
  const [search, setSearch] = useState("");

  const filtered = cities
    .filter((c) => c.city.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => b.count - a.count);

  const totalLeads = cities.reduce((acc, c) => acc + c.count, 0);
  const totalQualified = cities.reduce((acc, c) => acc + c.qualified_count, 0);

  return (
    <div
      className={cn(
        "absolute right-0 top-0 z-[1000] flex h-full transition-all duration-300",
        open ? "w-80" : "w-0"
      )}
    >
      {/* Toggle button */}
      <button
        onClick={onToggle}
        className="absolute -left-10 top-4 z-[1001] flex h-10 w-10 items-center justify-center rounded-l-xl bg-card border border-r-0 border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
        title={open ? "Cerrar panel" : "Abrir panel"}
      >
        {open ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
      </button>

      {/* Panel content */}
      {open && (
        <div className="flex w-80 flex-col overflow-hidden bg-card border-l border-border">
          {/* Header */}
          <div className="border-b border-border px-4 py-3">
            <h3 className="font-heading text-sm font-semibold text-foreground">
              Ciudades ({filtered.length})
            </h3>
            <div className="mt-1 flex gap-4 text-xs text-muted-foreground">
              <span>{totalLeads} leads</span>
              <span>{totalQualified} calificados</span>
            </div>
          </div>

          {/* Search */}
          <div className="border-b border-border px-4 py-2">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                placeholder="Buscar ciudad..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full rounded-lg border border-border bg-muted/50 py-1.5 pl-8 pr-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-violet-500/30"
              />
            </div>
          </div>

          {/* City list */}
          <div className="flex-1 overflow-y-auto">
            {filtered.length === 0 ? (
              <p className="px-4 py-8 text-center text-sm text-muted-foreground">
                Sin resultados
              </p>
            ) : (
              <ul className="divide-y divide-border">
                {filtered.map((city) => (
                  <li
                    key={city.city}
                    className="flex items-center justify-between px-4 py-2.5 hover:bg-muted/50 transition-colors"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-foreground">{city.city}</p>
                      <p className="text-xs text-muted-foreground">
                        Score: {city.avg_score.toFixed(1)} &middot; Calif: {city.qualified_count}
                      </p>
                    </div>
                    <span className="ml-2 flex-shrink-0 rounded-full bg-violet-50 dark:bg-violet-950/40 px-2 py-0.5 text-xs font-semibold text-violet-700 dark:text-violet-300">
                      {city.count}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

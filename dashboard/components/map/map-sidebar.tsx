"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, Search, MapPin } from "lucide-react";
import { cn } from "@/lib/utils";
import type { GeoSummaryCity } from "@/types";

interface MapSidebarProps {
  cities: GeoSummaryCity[];
  open: boolean;
  onToggle: () => void;
}

function getScoreColor(score: number): string {
  if (score >= 70) return "text-emerald-600 dark:text-emerald-400";
  if (score >= 40) return "text-yellow-600 dark:text-yellow-400";
  return "text-red-600 dark:text-red-400";
}

function getScoreDot(score: number): string {
  if (score >= 70) return "bg-emerald-500";
  if (score >= 40) return "bg-yellow-500";
  return "bg-red-500";
}

export function MapSidebar({ cities, open, onToggle }: MapSidebarProps) {
  const [search, setSearch] = useState("");

  const filtered = cities
    .filter((c) => c.city.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => b.count - a.count);

  const totalLeads = cities.reduce((acc, c) => acc + c.count, 0);
  const totalQualified = cities.reduce((acc, c) => acc + c.qualified_count, 0);
  const avgScore =
    cities.length > 0
      ? cities.reduce((acc, c) => acc + c.avg_score, 0) / cities.length
      : 0;

  return (
    <>
      {/* Toggle button */}
      <button
        onClick={onToggle}
        className={cn(
          "absolute top-4 z-[1001] flex h-10 w-10 items-center justify-center rounded-l-xl border border-r-0 border-border bg-card/90 backdrop-blur-md text-muted-foreground shadow-lg transition-all duration-[350ms] ease-in-out hover:text-foreground hover:bg-muted",
          open ? "right-[20rem]" : "right-0"
        )}
        title={open ? "Cerrar panel" : "Abrir panel"}
      >
        {open ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
      </button>

      {/* Panel content */}
      <div
        className={cn(
          "absolute right-0 top-0 z-[1000] h-full w-80 transition-transform duration-[350ms] ease-in-out",
          open ? "translate-x-0" : "translate-x-full"
        )}
      >
        <div className="flex h-full w-full flex-col overflow-hidden backdrop-blur-xl border-l border-border bg-card/95">
          {/* Header */}
          <div className="border-b border-border px-4 py-3">
            <div className="flex items-center gap-2 mb-2">
              <MapPin className="h-4 w-4 text-foreground" />
              <h3 className="text-sm font-bold text-foreground">
                Ciudades ({cities.length})
              </h3>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div className="rounded-lg px-2.5 py-1.5 text-center bg-muted/50">
                <p className="text-xs text-muted-foreground">Leads</p>
                <p className="text-sm font-bold tabular-nums text-foreground font-data">{totalLeads}</p>
              </div>
              <div className="rounded-lg px-2.5 py-1.5 text-center bg-muted/50">
                <p className="text-xs text-muted-foreground">Calif.</p>
                <p className="text-sm font-bold tabular-nums text-emerald-600 dark:text-emerald-400">{totalQualified}</p>
              </div>
              <div className="rounded-lg px-2.5 py-1.5 text-center bg-muted/50">
                <p className="text-xs text-muted-foreground">Score</p>
                <p className="text-sm font-bold tabular-nums text-foreground font-data">{avgScore.toFixed(0)}</p>
              </div>
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
                className="w-full rounded-lg border border-border bg-muted/50 py-1.5 pl-8 pr-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring/50 focus:border-ring"
              />
            </div>
          </div>

          {/* City list */}
          <div className="flex-1 overflow-y-auto scrollbar-thin">
            {filtered.length === 0 ? (
              <p className="px-4 py-8 text-center text-sm text-muted-foreground">
                Sin resultados
              </p>
            ) : (
              <ul>
                {filtered.map((city, i) => (
                  <li
                    key={city.city}
                    className={cn(
                      "flex items-center justify-between px-4 py-2.5 transition-colors hover:bg-muted/50",
                      i < filtered.length - 1 && "border-b border-border/40"
                    )}
                  >
                    <div className="min-w-0 flex items-center gap-2.5">
                      <span
                        className={cn(
                          "inline-block h-2 w-2 rounded-full flex-shrink-0",
                          getScoreDot(city.avg_score)
                        )}
                      />
                      <div>
                        <p className="truncate text-sm font-medium text-foreground">{city.city}</p>
                        <p className="text-[11px] text-muted-foreground">
                          Score{" "}
                          <span className={cn("font-medium", getScoreColor(city.avg_score))}>
                            {city.avg_score.toFixed(1)}
                          </span>
                          {" · "}
                          {city.qualified_count} calif.
                        </p>
                      </div>
                    </div>
                    <span className="ml-2 flex-shrink-0 rounded-full px-2.5 py-0.5 text-xs font-bold tabular-nums bg-muted text-foreground">
                      {city.count}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

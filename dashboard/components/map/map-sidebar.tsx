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
  if (score >= 70) return "text-emerald-400";
  if (score >= 40) return "text-yellow-400";
  return "text-red-400";
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
    <div
      className={cn(
        "absolute right-0 top-0 z-[1000] flex h-full transition-all duration-300",
        open ? "w-80" : "w-0"
      )}
    >
      {/* Toggle button */}
      <button
        onClick={onToggle}
        className="absolute -left-10 top-4 z-[1001] flex h-10 w-10 items-center justify-center rounded-l-xl bg-black/60 backdrop-blur-md border border-r-0 border-white/10 text-white/50 hover:text-white hover:bg-black/70 transition-all"
        title={open ? "Cerrar panel" : "Abrir panel"}
      >
        {open ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
      </button>

      {/* Panel content */}
      {open && (
        <div className="flex w-80 flex-col overflow-hidden bg-black/50 backdrop-blur-xl border-l border-white/10">
          {/* Header */}
          <div className="border-b border-white/10 px-4 py-3">
            <div className="flex items-center gap-2 mb-2">
              <MapPin className="h-4 w-4 text-violet-400" />
              <h3 className="text-sm font-bold text-white">
                Ciudades ({cities.length})
              </h3>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div className="rounded-lg bg-white/5 px-2.5 py-1.5 text-center">
                <p className="text-xs text-white/40">Leads</p>
                <p className="text-sm font-bold text-white tabular-nums">{totalLeads}</p>
              </div>
              <div className="rounded-lg bg-white/5 px-2.5 py-1.5 text-center">
                <p className="text-xs text-white/40">Calif.</p>
                <p className="text-sm font-bold text-emerald-400 tabular-nums">{totalQualified}</p>
              </div>
              <div className="rounded-lg bg-white/5 px-2.5 py-1.5 text-center">
                <p className="text-xs text-white/40">Score</p>
                <p className="text-sm font-bold text-violet-400 tabular-nums">{avgScore.toFixed(0)}</p>
              </div>
            </div>
          </div>

          {/* Search */}
          <div className="border-b border-white/10 px-4 py-2">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-white/30" />
              <input
                type="text"
                placeholder="Buscar ciudad..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full rounded-lg border border-white/10 bg-white/5 py-1.5 pl-8 pr-3 text-sm text-white placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-500/40"
              />
            </div>
          </div>

          {/* City list */}
          <div className="flex-1 overflow-y-auto scrollbar-thin">
            {filtered.length === 0 ? (
              <p className="px-4 py-8 text-center text-sm text-white/30">
                Sin resultados
              </p>
            ) : (
              <ul>
                {filtered.map((city, i) => (
                  <li
                    key={city.city}
                    className={cn(
                      "flex items-center justify-between px-4 py-2.5 hover:bg-white/5 transition-colors",
                      i < filtered.length - 1 && "border-b border-white/5"
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
                        <p className="truncate text-sm font-medium text-white/90">{city.city}</p>
                        <p className="text-[11px] text-white/35">
                          Score{" "}
                          <span className={cn("font-medium", getScoreColor(city.avg_score))}>
                            {city.avg_score.toFixed(1)}
                          </span>
                          {" · "}
                          {city.qualified_count} calif.
                        </p>
                      </div>
                    </div>
                    <span className="ml-2 flex-shrink-0 rounded-full bg-violet-500/15 px-2.5 py-0.5 text-xs font-bold text-violet-300 tabular-nums">
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

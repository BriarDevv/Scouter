"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, Search, MapPin } from "lucide-react";
import { cn } from "@/lib/utils";
import type { GeoSummaryCity } from "@/types";

interface MapSidebarProps {
  cities: GeoSummaryCity[];
  open: boolean;
  onToggle: () => void;
  isDarkMap?: boolean;
}

function getScoreColor(score: number, dark: boolean): string {
  if (score >= 70) return dark ? "text-emerald-400" : "text-emerald-600";
  if (score >= 40) return dark ? "text-yellow-400" : "text-yellow-600";
  return dark ? "text-red-400" : "text-red-600";
}

function getScoreDot(score: number): string {
  if (score >= 70) return "bg-emerald-500";
  if (score >= 40) return "bg-yellow-500";
  return "bg-red-500";
}

export function MapSidebar({ cities, open, onToggle, isDarkMap = true }: MapSidebarProps) {
  const [search, setSearch] = useState("");
  const d = isDarkMap;

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
        className={cn(
          "absolute -left-10 top-4 z-[1001] flex h-10 w-10 items-center justify-center rounded-l-xl backdrop-blur-md border border-r-0 transition-all",
          d
            ? "bg-black/60 border-white/10 text-white/50 hover:text-white hover:bg-black/70"
            : "bg-white/80 border-black/10 text-black/40 hover:text-black hover:bg-white/90"
        )}
        title={open ? "Cerrar panel" : "Abrir panel"}
      >
        {open ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
      </button>

      {/* Panel content */}
      {open && (
        <div
          className={cn(
            "flex w-80 flex-col overflow-hidden backdrop-blur-xl border-l transition-colors",
            d
              ? "bg-black/50 border-white/10"
              : "bg-white/85 border-black/10"
          )}
        >
          {/* Header */}
          <div className={cn("border-b px-4 py-3", d ? "border-white/10" : "border-black/8")}>
            <div className="flex items-center gap-2 mb-2">
              <MapPin className={cn("h-4 w-4", d ? "text-muted-foreground" : "text-foreground")} />
              <h3 className={cn("text-sm font-bold", d ? "text-white" : "text-foreground")}>
                Ciudades ({cities.length})
              </h3>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div className={cn("rounded-lg px-2.5 py-1.5 text-center", d ? "bg-white/5" : "bg-black/5")}>
                <p className={cn("text-xs", d ? "text-white/40" : "text-black/40")}>Leads</p>
                <p className={cn("text-sm font-bold tabular-nums", d ? "text-white" : "text-foreground")}>{totalLeads}</p>
              </div>
              <div className={cn("rounded-lg px-2.5 py-1.5 text-center", d ? "bg-white/5" : "bg-black/5")}>
                <p className={cn("text-xs", d ? "text-white/40" : "text-black/40")}>Calif.</p>
                <p className={cn("text-sm font-bold tabular-nums", d ? "text-emerald-400" : "text-emerald-600")}>{totalQualified}</p>
              </div>
              <div className={cn("rounded-lg px-2.5 py-1.5 text-center", d ? "bg-white/5" : "bg-black/5")}>
                <p className={cn("text-xs", d ? "text-white/40" : "text-black/40")}>Score</p>
                <p className={cn("text-sm font-bold tabular-nums", d ? "text-muted-foreground" : "text-foreground")}>{avgScore.toFixed(0)}</p>
              </div>
            </div>
          </div>

          {/* Search */}
          <div className={cn("border-b px-4 py-2", d ? "border-white/10" : "border-black/8")}>
            <div className="relative">
              <Search className={cn("absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2", d ? "text-white/30" : "text-black/30")} />
              <input
                type="text"
                placeholder="Buscar ciudad..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className={cn(
                  "w-full rounded-lg border py-1.5 pl-8 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring/50 focus:border-ring",
                  d
                    ? "border-white/10 bg-white/5 text-white placeholder:text-white/30"
                    : "border-border bg-muted text-foreground placeholder:text-muted-foreground"
                )}
              />
            </div>
          </div>

          {/* City list */}
          <div className="flex-1 overflow-y-auto scrollbar-thin">
            {filtered.length === 0 ? (
              <p className={cn("px-4 py-8 text-center text-sm", d ? "text-white/30" : "text-black/30")}>
                Sin resultados
              </p>
            ) : (
              <ul>
                {filtered.map((city, i) => (
                  <li
                    key={city.city}
                    className={cn(
                      "flex items-center justify-between px-4 py-2.5 transition-colors",
                      d ? "hover:bg-white/5" : "hover:bg-black/5",
                      i < filtered.length - 1 && (d ? "border-b border-white/5" : "border-b border-black/5")
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
                        <p className={cn("truncate text-sm font-medium", d ? "text-white/90" : "text-foreground")}>{city.city}</p>
                        <p className={cn("text-[11px]", d ? "text-white/35" : "text-black/40")}>
                          Score{" "}
                          <span className={cn("font-medium", getScoreColor(city.avg_score, d))}>
                            {city.avg_score.toFixed(1)}
                          </span>
                          {" · "}
                          {city.qualified_count} calif.
                        </p>
                      </div>
                    </div>
                    <span className={cn(
                      "ml-2 flex-shrink-0 rounded-full px-2.5 py-0.5 text-xs font-bold tabular-nums",
                      d
                        ? "bg-muted text-muted-foreground"
                        : "bg-muted text-foreground"
                    )}>
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

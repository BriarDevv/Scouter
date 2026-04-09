"use client";

import { useEffect, useState } from "react";
import { MapPin } from "lucide-react";
import { getTerritories } from "@/lib/api/client";
import type { TerritoryWithStats } from "@/types";
import Link from "next/link";
import { cn } from "@/lib/utils";

export function TerritorySummary() {
  const [territories, setTerritories] = useState<TerritoryWithStats[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const data = await getTerritories();
        if (active) {
          setTerritories(
            data
              .filter((t) => t.is_active)
              .sort((a, b) => b.lead_count - a.lead_count)
              .slice(0, 5)
          );
        }
      } catch {
        // silent
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => { active = false; };
  }, []);

  if (loading) {
    return (
      <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
        <div className="h-5 w-32 rounded bg-muted animate-pulse mb-4" />
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-10 rounded-lg bg-muted/40 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (territories.length === 0) return null;

  const maxCount = Math.max(...territories.map((t) => t.lead_count), 1);

  return (
    <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground font-heading">Territorios</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">{territories.length} zonas activas</p>
        </div>
        <Link
          href="/map"
          className="text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
        >
          Ver mapa
        </Link>
      </div>

      <div className="mt-4 space-y-px">
        {territories.map((t) => {
          const pct = (t.lead_count / maxCount) * 100;

          return (
            <div
              key={t.id}
              className="relative flex items-center gap-3 rounded-lg px-3 py-2.5 transition-colors hover:bg-muted/50"
            >
              {/* Bar background */}
              <div className="absolute inset-0 rounded-lg overflow-hidden">
                <div
                  className="h-full bg-foreground/[0.04] transition-[width] duration-700"
                  style={{ width: `${pct}%` }}
                />
              </div>

              <MapPin className="relative h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              <div className="relative flex-1 min-w-0">
                <span className="text-xs font-medium text-foreground">{t.name}</span>
                <span className="text-[10px] text-muted-foreground ml-2">{t.cities?.length ?? 0} ciudades</span>
              </div>
              <div className="relative flex items-center gap-3 shrink-0">
                <span className={cn(
                  "text-[10px] font-data font-bold px-1.5 py-0.5 rounded-full",
                  t.avg_score >= 60 ? "bg-emerald-100 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300"
                    : t.avg_score >= 30 ? "bg-amber-100 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300"
                    : "bg-red-100 dark:bg-red-950/40 text-red-700 dark:text-red-300"
                )}>
                  score {t.avg_score.toFixed(0)}
                </span>
                <span className="font-data text-sm font-bold text-foreground tabular-nums">
                  {t.lead_count}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

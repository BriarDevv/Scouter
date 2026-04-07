"use client";

import { useEffect, useState } from "react";
import { MapPin } from "lucide-react";
import { getTerritories } from "@/lib/api/client";
import type { TerritoryWithStats } from "@/types";
import Link from "next/link";

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
      } catch (err) {
        console.error("territory_summary_fetch_failed", err);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => { active = false; };
  }, []);

  if (loading) {
    return (
      <div className="rounded-2xl border border-border bg-card p-5 shadow-sm animate-pulse">
        <div className="h-5 w-40 rounded bg-muted mb-4" />
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3">
              <div className="h-4 w-4 rounded-full bg-muted" />
              <div className="h-4 flex-1 rounded bg-muted" />
              <div className="h-4 w-12 rounded bg-muted" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (territories.length === 0) return null;

  const maxCount = Math.max(...territories.map((t) => t.lead_count), 1);

  return (
    <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-50 dark:bg-violet-950/30">
            <MapPin className="h-4 w-4 text-violet-600 dark:text-violet-400" />
          </div>
          <h3 className="text-sm font-semibold font-heading text-foreground">Territorios</h3>
        </div>
        <Link
          href="/map"
          className="text-xs font-medium text-violet-600 dark:text-violet-400 hover:underline"
        >
          Ver mapa
        </Link>
      </div>
      <div className="space-y-3">
        {territories.map((t) => (
          <div key={t.id} className="flex items-center gap-3">
            <span className="h-3 w-3 rounded-full shrink-0" style={{ backgroundColor: t.color }} />
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-foreground truncate">{t.name}</span>
                <span className="text-xs font-data text-muted-foreground ml-2">{t.lead_count}</span>
              </div>
              <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full rounded-full transition-[width] duration-500"
                  style={{
                    width: `${(t.lead_count / maxCount) * 100}%`,
                    backgroundColor: t.color,
                  }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

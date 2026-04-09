"use client";

import { useCallback } from "react";
import dynamic from "next/dynamic";
import { MapPin, RefreshCw } from "lucide-react";
import {
  createTerritory,
  updateTerritory,
  deleteTerritory,
} from "@/lib/api/client";
import { useApi } from "@/lib/hooks/use-swr-fetch";
import { TerritoryPanel } from "@/components/map/territory-panel";
import type { Lead, GeoSummaryCity, TerritoryWithStats } from "@/types";

const LeadMap = dynamic(
  () => import("@/components/map/lead-map").then((mod) => ({ default: mod.LeadMap })),
  { ssr: false, loading: () => <MapSkeleton /> }
);

function MapSkeleton() {
  return (
    <div className="flex h-full w-full items-center justify-center bg-muted/30">
      <div className="flex flex-col items-center gap-3 text-muted-foreground">
        <MapPin className="h-8 w-8 animate-pulse" />
        <p className="text-sm">Cargando mapa...</p>
      </div>
    </div>
  );
}

export default function MapPage() {
  const { data: cities, isLoading: citiesLoading, mutate: mutateCities } = useApi<GeoSummaryCity[]>("/dashboard/geo-summary");
  const { data: leadsData, isLoading: leadsLoading, mutate: mutateLeads } = useApi<{ items: Lead[]; total: number }>("/leads?page=1&page_size=200");
  const leads = leadsData?.items;
  const { data: territories, isLoading: territoriesLoading, mutate: mutateTerritories } = useApi<TerritoryWithStats[]>("/territories");

  const loading = citiesLoading || leadsLoading || territoriesLoading;

  const loadData = useCallback(async () => {
    await Promise.all([mutateCities(), mutateLeads(), mutateTerritories()]);
  }, [mutateCities, mutateLeads, mutateTerritories]);

  async function handleCreateTerritory(data: {
    name: string;
    description: string;
    color: string;
    cities: string[];
    is_active: boolean;
  }) {
    await createTerritory(data);
    await loadData();
  }

  async function handleUpdateTerritory(id: string, data: Partial<import("@/types").Territory>) {
    await updateTerritory(id, data);
    await loadData();
  }

  async function handleDeleteTerritory(id: string) {
    await deleteTerritory(id);
    await loadData();
  }

  return (
    <div className="flex h-[calc(100vh-1rem)] flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border bg-card px-6 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-muted dark:bg-muted">
            <MapPin className="h-5 w-5 text-foreground" />
          </div>
          <div>
            <h1 className="font-heading text-lg font-bold text-foreground">Mapa de Leads</h1>
            <p className="text-xs text-muted-foreground">
              {(leads ?? []).length} negocios con ubicacion &middot; {(cities ?? []).length} ciudades
            </p>
          </div>
        </div>
        <button
          onClick={() => void loadData()}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          Actualizar
        </button>
      </div>

      {/* Map */}
      <div className="relative flex-1">
        <LeadMap cities={cities ?? []} leads={leads ?? []} territories={territories ?? []} />
        <TerritoryPanel
          territories={territories ?? []}
          onSave={handleCreateTerritory}
          onUpdate={handleUpdateTerritory}
          onDelete={handleDeleteTerritory}
        />
      </div>
    </div>
  );
}

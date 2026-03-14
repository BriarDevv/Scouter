"use client";

import { useState } from "react";
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  ZoomControl,
} from "react-leaflet";
import { CityMarker } from "@/components/map/city-marker";
import { MapSidebar } from "@/components/map/map-sidebar";
import { HeatmapLayer } from "@/components/map/heatmap-layer";
import type { GeoSummaryCity, TerritoryWithStats } from "@/types";
import "leaflet/dist/leaflet.css";
import "@/components/map/map-dark.css";

interface LeadMapProps {
  cities: GeoSummaryCity[];
  territories?: TerritoryWithStats[];
}

const TILE_PROVIDERS = {
  dark: {
    url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
  },
  light: {
    url: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
  },
  satellite: {
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attribution:
      '&copy; <a href="https://www.esri.com/">Esri</a>',
  },
} as const;

type TileKey = keyof typeof TILE_PROVIDERS;

export function LeadMap({ cities, territories = [] }: LeadMapProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [tileKey, setTileKey] = useState<TileKey>("dark");
  const [showHeat, setShowHeat] = useState(false);
  const [showTerritories, setShowTerritories] = useState(true);

  const tile = TILE_PROVIDERS[tileKey];

  // Build a lookup: city name -> territory color
  const cityTerritoryColor: Record<string, string> = {};
  for (const territory of territories) {
    if (!territory.is_active) continue;
    for (const city of territory.cities) {
      if (!cityTerritoryColor[city]) {
        cityTerritoryColor[city] = territory.color;
      }
    }
  }

  // Build heatmap points from cities
  const heatPoints = cities.map((c) => ({
    lat: c.lat,
    lng: c.lng,
    intensity: c.count / Math.max(1, ...cities.map((x) => x.count)),
  }));

  return (
    <div className="relative h-full w-full">
      <MapContainer
        center={[-38.4, -63.6]}
        zoom={5}
        className="h-full w-full z-0 map-dark-theme"
        scrollWheelZoom={true}
        zoomControl={false}
      >
        <ZoomControl position="bottomright" />

        <TileLayer
          key={tileKey}
          attribution={tile.attribution}
          url={tile.url}
        />

        {/* Territory overlays */}
        {showTerritories &&
          territories
            .filter((t) => t.is_active)
            .flatMap((territory) =>
              territory.cities.map((cityName) => {
                const cityData = cities.find((c) => c.city === cityName);
                if (!cityData) return null;
                return (
                  <CircleMarker
                    key={`territory-${territory.id}-${cityName}`}
                    center={[cityData.lat, cityData.lng]}
                    radius={35}
                    pathOptions={{
                      color: territory.color,
                      fillColor: territory.color,
                      fillOpacity: 0.12,
                      weight: 1.5,
                      dashArray: "6 4",
                    }}
                  >
                    <Popup>
                      <div className="map-popup-content">
                        <p className="font-bold">{territory.name}</p>
                        <p className="text-muted-foreground">{cityName}</p>
                      </div>
                    </Popup>
                  </CircleMarker>
                );
              })
            )}

        {/* Heatmap layer */}
        <HeatmapLayer points={heatPoints} visible={showHeat} />

        {/* City markers */}
        {cities.map((city) => (
          <CityMarker
            key={city.city}
            city={city.city}
            count={city.count}
            avg_score={city.avg_score}
            qualified_count={city.qualified_count}
            lat={city.lat}
            lng={city.lng}
            territoryColor={
              showTerritories ? cityTerritoryColor[city.city] : undefined
            }
          />
        ))}
      </MapContainer>

      {/* ── Layer controls (top-left) ─────────────────────────── */}
      <div className="absolute left-3 top-3 z-[1000] flex items-center gap-1.5 rounded-xl border border-white/10 bg-black/60 backdrop-blur-md px-2 py-1.5 shadow-lg">
        {(["dark", "light", "satellite"] as TileKey[]).map((key) => (
          <button
            key={key}
            onClick={() => setTileKey(key)}
            className={`rounded-lg px-2.5 py-1 text-[11px] font-medium transition-all ${
              tileKey === key
                ? "bg-violet-600 text-white shadow-sm"
                : "text-white/60 hover:text-white hover:bg-white/10"
            }`}
          >
            {key === "dark" ? "Oscuro" : key === "light" ? "Claro" : "Satelite"}
          </button>
        ))}
        <div className="mx-1 h-4 w-px bg-white/20" />
        <button
          onClick={() => setShowHeat((p) => !p)}
          className={`rounded-lg px-2.5 py-1 text-[11px] font-medium transition-all ${
            showHeat
              ? "bg-orange-500/80 text-white shadow-sm"
              : "text-white/60 hover:text-white hover:bg-white/10"
          }`}
        >
          Calor
        </button>
        <button
          onClick={() => setShowTerritories((p) => !p)}
          className={`rounded-lg px-2.5 py-1 text-[11px] font-medium transition-all ${
            showTerritories
              ? "bg-emerald-500/80 text-white shadow-sm"
              : "text-white/60 hover:text-white hover:bg-white/10"
          }`}
        >
          Territorios
        </button>
      </div>

      {/* ── Legend (bottom-right, above zoom) ──────────────────── */}
      <div className="absolute right-3 bottom-20 z-[1000] rounded-xl border border-white/10 bg-black/60 backdrop-blur-md px-3 py-2 shadow-lg">
        <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-white/50">
          Score promedio
        </p>
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-emerald-500 shadow-[0_0_6px_rgba(34,197,94,0.5)]" />
            <span className="text-[11px] text-white/70">&ge; 70 — Alto</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-yellow-500 shadow-[0_0_6px_rgba(234,179,8,0.5)]" />
            <span className="text-[11px] text-white/70">&ge; 40 — Medio</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.5)]" />
            <span className="text-[11px] text-white/70">&lt; 40 — Bajo</span>
          </div>
        </div>
      </div>

      <MapSidebar
        cities={cities}
        open={sidebarOpen}
        onToggle={() => setSidebarOpen((prev) => !prev)}
      />
    </div>
  );
}

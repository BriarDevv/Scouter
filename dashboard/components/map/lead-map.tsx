"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  ZoomControl,
  useMap,
} from "react-leaflet";
import { CityMarker } from "@/components/map/city-marker";
import { LeadPin } from "@/components/map/lead-pin";
import { MapSidebar } from "@/components/map/map-sidebar";
import { HeatmapLayer } from "@/components/map/heatmap-layer";
import type { Lead, GeoSummaryCity, TerritoryWithStats } from "@/types";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "@/components/map/map-theme.css";

interface LeadMapProps {
  cities: GeoSummaryCity[];
  leads?: Lead[];
  territories?: TerritoryWithStats[];
  onSelectLead?: (lead: Lead) => void;
}

const TILE_PROVIDERS = {
  dark: {
    url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
    isDark: true,
  },
  light: {
    url: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
    isDark: false,
  },
  satellite: {
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attribution:
      '&copy; <a href="https://www.esri.com/">Esri</a>',
    isDark: true,
  },
} as const;

type TileKey = keyof typeof TILE_PROVIDERS;

const STORAGE_KEY = "clawscout-map-tile";

function loadTileKey(): TileKey {
  if (typeof window === "undefined") return "dark";
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved && saved in TILE_PROVIDERS) return saved as TileKey;
  return "dark";
}

function FitToLeads({ leads, active }: { leads: Lead[]; active: boolean }) {
  const map = useMap();
  const fitted = useRef(false);

  useEffect(() => {
    if (!active || leads.length === 0) {
      fitted.current = false;
      return;
    }
    if (fitted.current) return;
    const points = leads
      .filter((l) => l.latitude !== null && l.longitude !== null)
      .map((l) => [l.latitude!, l.longitude!] as [number, number]);
    if (points.length === 0) return;
    const bounds = L.latLngBounds(points);
    map.fitBounds(bounds, { padding: [50, 50], maxZoom: 14 });
    fitted.current = true;
  }, [leads, active, map]);

  return null;
}

export function LeadMap({ cities, leads = [], territories = [], onSelectLead }: LeadMapProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [tileKey, setTileKey] = useState<TileKey>(loadTileKey);
  const [showHeat, setShowHeat] = useState(false);
  const [showTerritories, setShowTerritories] = useState(true);
  const [viewMode, setViewMode] = useState<"cities" | "leads">("leads");

  const tile = TILE_PROVIDERS[tileKey];
  const isDark = tile.isDark;

  const changeTile = useCallback((key: TileKey) => {
    setTileKey(key);
    localStorage.setItem(STORAGE_KEY, key);
  }, []);

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
        className={`h-full w-full z-0 ${isDark ? "map-dark-theme" : "map-light-theme"}`}
        scrollWheelZoom={true}
        zoomControl={false}
      >
        <ZoomControl position="bottomright" />
        <FitToLeads leads={leads} active={viewMode === "leads"} />

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
                        <p className="opacity-60">{cityName}</p>
                      </div>
                    </Popup>
                  </CircleMarker>
                );
              })
            )}

        {/* Heatmap layer */}
        <HeatmapLayer points={heatPoints} visible={showHeat} />

        {/* City markers (aggregated view) */}
        {viewMode === "cities" && cities.map((city) => (
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

        {/* Individual lead pins */}
        {viewMode === "leads" &&
          leads.map((lead) => (
            <LeadPin key={lead.id} lead={lead} onSelect={onSelectLead} />
          ))}
      </MapContainer>

      {/* ── Layer controls (top-left) ─────────────────────────── */}
      <div
        className={`absolute left-3 top-3 z-[1000] flex items-center gap-1.5 rounded-xl border backdrop-blur-md px-2 py-1.5 shadow-lg transition-colors ${
          isDark
            ? "border-white/10 bg-black/60"
            : "border-black/10 bg-white/80"
        }`}
      >
        {(["dark", "light", "satellite"] as TileKey[]).map((key) => (
          <button
            key={key}
            onClick={() => changeTile(key)}
            className={`rounded-lg px-2.5 py-1 text-[11px] font-medium transition-all ${
              tileKey === key
                ? "bg-violet-600 text-white shadow-sm"
                : isDark
                  ? "text-white/60 hover:text-white hover:bg-white/10"
                  : "text-black/50 hover:text-black hover:bg-black/5"
            }`}
          >
            {key === "dark" ? "Oscuro" : key === "light" ? "Claro" : "Satelite"}
          </button>
        ))}
        <div className={`mx-1 h-4 w-px ${isDark ? "bg-white/20" : "bg-black/10"}`} />
        <button
          onClick={() => setViewMode(viewMode === "leads" ? "cities" : "leads")}
          className={`rounded-lg px-2.5 py-1 text-[11px] font-medium transition-all ${
            viewMode === "leads"
              ? "bg-violet-600 text-white shadow-sm"
              : isDark
                ? "text-white/60 hover:text-white hover:bg-white/10"
                : "text-black/50 hover:text-black hover:bg-black/5"
          }`}
        >
          {viewMode === "leads" ? "Negocios" : "Ciudades"}
        </button>
        <div className={`mx-1 h-4 w-px ${isDark ? "bg-white/20" : "bg-black/10"}`} />
        <button
          onClick={() => setShowHeat((p) => !p)}
          className={`rounded-lg px-2.5 py-1 text-[11px] font-medium transition-all ${
            showHeat
              ? "bg-orange-500/80 text-white shadow-sm"
              : isDark
                ? "text-white/60 hover:text-white hover:bg-white/10"
                : "text-black/50 hover:text-black hover:bg-black/5"
          }`}
        >
          Calor
        </button>
        <button
          onClick={() => setShowTerritories((p) => !p)}
          className={`rounded-lg px-2.5 py-1 text-[11px] font-medium transition-all ${
            showTerritories
              ? "bg-emerald-500/80 text-white shadow-sm"
              : isDark
                ? "text-white/60 hover:text-white hover:bg-white/10"
                : "text-black/50 hover:text-black hover:bg-black/5"
          }`}
        >
          Territorios
        </button>
      </div>

      {/* ── Legend (bottom-right, above zoom) ──────────────────── */}
      <div
        className={`absolute right-3 bottom-20 z-[1000] rounded-xl border backdrop-blur-md px-3 py-2 shadow-lg transition-colors ${
          isDark
            ? "border-white/10 bg-black/60"
            : "border-black/10 bg-white/80"
        }`}
      >
        <p className={`mb-1.5 text-[10px] font-semibold uppercase tracking-wider ${isDark ? "text-white/50" : "text-black/40"}`}>
          {viewMode === "leads" ? "Score del lead" : "Score promedio"}
        </p>
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-emerald-500 shadow-[0_0_6px_rgba(34,197,94,0.5)]" />
            <span className={`text-[11px] ${isDark ? "text-white/70" : "text-black/60"}`}>&ge; 70 — Alto</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-yellow-500 shadow-[0_0_6px_rgba(234,179,8,0.5)]" />
            <span className={`text-[11px] ${isDark ? "text-white/70" : "text-black/60"}`}>&ge; 40 — Medio</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.5)]" />
            <span className={`text-[11px] ${isDark ? "text-white/70" : "text-black/60"}`}>&lt; 40 — Bajo</span>
          </div>
        </div>
      </div>

      <MapSidebar
        cities={cities}
        open={sidebarOpen}
        onToggle={() => setSidebarOpen((prev) => !prev)}
        isDarkMap={isDark}
      />
    </div>
  );
}

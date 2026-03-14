"use client";

import { useEffect, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import { CityMarker } from "@/components/map/city-marker";
import { MapSidebar } from "@/components/map/map-sidebar";
import type { GeoSummaryCity, TerritoryWithStats } from "@/types";
import "leaflet/dist/leaflet.css";

interface LeadMapProps {
  cities: GeoSummaryCity[];
  territories?: TerritoryWithStats[];
}

export function LeadMap({ cities, territories = [] }: LeadMapProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Build a lookup: city name -> territory color
  const cityTerritoryColor: Record<string, string> = {};
  for (const territory of territories) {
    if (!territory.is_active) continue;
    for (const city of territory.cities) {
      // First match wins
      if (!cityTerritoryColor[city]) {
        cityTerritoryColor[city] = territory.color;
      }
    }
  }

  return (
    <div className="relative h-full w-full">
      <MapContainer
        center={[-38.4, -63.6]}
        zoom={5}
        className="h-full w-full z-0"
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Territory overlays — faint circles for cities belonging to a territory */}
        {territories
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
                    fillOpacity: 0.08,
                    weight: 1,
                    dashArray: "5 5",
                  }}
                >
                  <Popup>
                    <div className="text-sm">
                      <p className="font-bold">{territory.name}</p>
                      <p className="text-muted-foreground">{cityName}</p>
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })
          )}

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
            territoryColor={cityTerritoryColor[city.city]}
          />
        ))}
      </MapContainer>

      <MapSidebar
        cities={cities}
        open={sidebarOpen}
        onToggle={() => setSidebarOpen((prev) => !prev)}
      />
    </div>
  );
}

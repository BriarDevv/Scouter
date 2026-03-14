"use client";

import { CircleMarker, Popup } from "react-leaflet";

interface CityMarkerProps {
  city: string;
  count: number;
  avg_score: number;
  qualified_count: number;
  lat: number;
  lng: number;
  territoryColor?: string;
}

function getScoreColor(score: number): string {
  if (score >= 70) return "#22c55e";
  if (score >= 40) return "#eab308";
  return "#ef4444";
}

function getRadius(count: number): number {
  return Math.min(Math.max(Math.sqrt(count) * 4, 8), 30);
}

export function CityMarker({
  city,
  count,
  avg_score,
  qualified_count,
  lat,
  lng,
  territoryColor,
}: CityMarkerProps) {
  const color = territoryColor ?? getScoreColor(avg_score);
  const radius = getRadius(count);

  return (
    <CircleMarker
      center={[lat, lng]}
      radius={radius}
      pathOptions={{
        color,
        fillColor: color,
        fillOpacity: 0.35,
        weight: 2,
      }}
    >
      <Popup>
        <div className="min-w-[180px] space-y-1 text-sm">
          <p className="font-bold text-base">{city}</p>
          <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 pt-1">
            <span className="text-muted-foreground">Leads</span>
            <span className="font-semibold text-right">{count}</span>
            <span className="text-muted-foreground">Score prom.</span>
            <span className="font-semibold text-right">{avg_score.toFixed(1)}</span>
            <span className="text-muted-foreground">Calificados</span>
            <span className="font-semibold text-right">{qualified_count}</span>
          </div>
        </div>
      </Popup>
    </CircleMarker>
  );
}

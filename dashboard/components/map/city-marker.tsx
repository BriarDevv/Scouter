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

function getScoreLabel(score: number): string {
  if (score >= 70) return "Alto";
  if (score >= 40) return "Medio";
  return "Bajo";
}

function getRadius(count: number): number {
  return Math.min(Math.max(Math.sqrt(count) * 5, 8), 32);
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
    <>
      {/* Outer glow ring */}
      <CircleMarker
        center={[lat, lng]}
        radius={radius + 4}
        pathOptions={{
          color: "transparent",
          fillColor: color,
          fillOpacity: 0.12,
          weight: 0,
        }}
        interactive={false}
      />

      {/* Main marker */}
      <CircleMarker
        center={[lat, lng]}
        radius={radius}
        pathOptions={{
          color,
          fillColor: color,
          fillOpacity: 0.45,
          weight: 2,
        }}
      >
        <Popup>
          <div className="map-popup-content">
            <p style={{ fontSize: 14, fontWeight: 700, marginBottom: 2 }}>{city}</p>
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 5,
                marginBottom: 8,
                padding: "2px 8px",
                borderRadius: 20,
                fontSize: 11,
                fontWeight: 600,
                background: `${color}22`,
                color,
              }}
            >
              <span
                style={{
                  width: 7,
                  height: 7,
                  borderRadius: "50%",
                  background: color,
                  boxShadow: `0 0 6px ${color}80`,
                }}
              />
              {getScoreLabel(avg_score)}
            </div>
            <div className="stat-grid">
              <span className="stat-label">Leads</span>
              <span className="stat-value">{count}</span>
              <span className="stat-label">Score prom.</span>
              <span className="stat-value">{avg_score.toFixed(1)}</span>
              <span className="stat-label">Calificados</span>
              <span className="stat-value">{qualified_count}</span>
            </div>
          </div>
        </Popup>
      </CircleMarker>
    </>
  );
}

"use client";

import { useEffect } from "react";
import { useMap } from "react-leaflet";
import type { Layer, Map as LeafletMap } from "leaflet";

interface HeatmapPoint {
  lat: number;
  lng: number;
  intensity: number;
}

interface HeatmapLayerProps {
  points: HeatmapPoint[];
  visible: boolean;
  radius?: number;
  blur?: number;
  maxZoom?: number;
}

export function HeatmapLayer({
  points,
  visible,
  radius = 25,
  blur = 15,
  maxZoom = 12,
}: HeatmapLayerProps) {
  const map = useMap();

  useEffect(() => {
    if (!visible || points.length === 0) return;

    // leaflet.heat augments L with `heatLayer`; the return is a dynamic L.Layer.
    let heatLayer: Layer | null = null;

    async function addHeat() {
      try {
        const L = await import("leaflet");
        // @ts-expect-error leaflet.heat adds L.heatLayer
        await import("@/lib/vendor/leaflet-heat");

        const heatData = points.map(
          (p) => [p.lat, p.lng, p.intensity] as [number, number, number]
        );

        // @ts-ignore -- leaflet.heat augments L at runtime
        heatLayer = L.heatLayer(heatData, {
          radius,
          blur,
          maxZoom,
          gradient: {
            0.2: "#3b82f6",
            0.4: "#22d3ee",
            0.6: "#22c55e",
            0.8: "#eab308",
            1.0: "#ef4444",
          },
        }).addTo(map as unknown as LeafletMap);
      } catch {
        // leaflet.heat not installed — skip silently
      }
    }

    void addHeat();

    return () => {
      if (heatLayer) {
        (map as unknown as LeafletMap).removeLayer(heatLayer);
      }
    };
  }, [map, points, visible, radius, blur, maxZoom]);

  return null;
}

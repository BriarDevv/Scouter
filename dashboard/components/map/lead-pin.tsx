"use client";

import { Marker, Popup } from "react-leaflet";
import L from "leaflet";
import type { Lead } from "@/types";

function scoreColor(score: number | null): string {
  if (score === null) return "#94a3b8";
  if (score >= 70) return "#22c55e";
  if (score >= 40) return "#eab308";
  return "#ef4444";
}

function createPinIcon(score: number | null) {
  const color = scoreColor(score);
  return L.divIcon({
    className: "",
    iconSize: [14, 14],
    iconAnchor: [7, 7],
    html: `<div style="
      width:10px;height:10px;
      background:${color};
      border:2px solid white;
      border-radius:50%;
      box-shadow:0 1px 4px rgba(0,0,0,0.35);
    "></div>`,
  });
}

interface LeadPinProps {
  lead: Lead;
  onSelect?: (lead: Lead) => void;
}

export function LeadPin({ lead, onSelect }: LeadPinProps) {
  if (lead.latitude === null || lead.longitude === null) return null;
  const color = scoreColor(lead.score);

  return (
    <Marker
      position={[lead.latitude, lead.longitude]}
      icon={createPinIcon(lead.score)}
      eventHandlers={{ click: () => onSelect?.(lead) }}
    >
      <Popup>
        <div style={{ minWidth: 200, fontFamily: "system-ui, sans-serif" }}>
          <p style={{ margin: 0, fontWeight: 700, fontSize: 13 }}>{lead.business_name}</p>
          {lead.industry && (
            <p style={{ margin: "2px 0 0", fontSize: 11, opacity: 0.6 }}>{lead.industry}</p>
          )}
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 6, fontSize: 11 }}>
            {lead.score !== null && (
              <span style={{ fontFamily: "monospace", fontWeight: 600, color }}>
                {lead.score} pts
              </span>
            )}
            {lead.rating !== null && <span>&#9733; {lead.rating}</span>}
            {lead.review_count !== null && <span>{lead.review_count} rese\u00f1as</span>}
          </div>
          {lead.address && (
            <p style={{ margin: "4px 0 0", fontSize: 11, opacity: 0.55, lineHeight: 1.35 }}>
              {lead.address}
            </p>
          )}
          {lead.phone && (
            <p style={{ margin: "2px 0 0", fontSize: 11, fontFamily: "monospace", opacity: 0.5 }}>
              {lead.phone}
            </p>
          )}
        </div>
      </Popup>
    </Marker>
  );
}

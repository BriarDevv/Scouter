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
        <div className="map-popup-content">
          <p className="popup-title">{lead.business_name}</p>
          {lead.industry && (
            <p className="popup-subtitle">{lead.industry}</p>
          )}
          <div className="popup-stats">
            {lead.score !== null && (
              <span className="popup-score" style={{ color }}>
                {lead.score} pts
              </span>
            )}
            {lead.rating !== null && <span className="popup-detail">★ {lead.rating}</span>}
            {lead.review_count !== null && <span className="popup-detail">{lead.review_count} reseñas</span>}
          </div>
          {lead.address && (
            <a
              href={lead.google_maps_url || `https://www.google.com/maps?q=${lead.latitude},${lead.longitude}`}
              target="_blank"
              rel="noopener noreferrer"
              className="popup-link popup-address"
            >
              {lead.address}
            </a>
          )}
          {lead.website_url && (
            <a
              href={lead.website_url}
              target="_blank"
              rel="noopener noreferrer"
              className="popup-link popup-web"
            >
              {lead.website_url.replace(/^https?:\/\/(www\.)?/, "").replace(/\/$/, "")}
            </a>
          )}
          <div className="popup-contact">
            {lead.email && (
              <a href={`mailto:${lead.email}`} className="popup-link popup-email">{lead.email}</a>
            )}
            {lead.phone && (
              <a href={`tel:${lead.phone}`} className="popup-link popup-phone">{lead.phone}</a>
            )}
          </div>
          <a href={`/leads/${lead.id}`} className="popup-cta">Ver lead</a>
        </div>
      </Popup>
    </Marker>
  );
}

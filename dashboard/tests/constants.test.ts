import { describe, it, expect } from "vitest";
import {
  STATUS_CONFIG,
  QUALITY_CONFIG,
  SIGNAL_CONFIG,
} from "@/lib/constants";
import type { LeadStatus, LeadQuality, SignalType } from "@/types";

const ALL_LEAD_STATUSES: LeadStatus[] = [
  "new", "enriched", "scored", "qualified", "draft_ready",
  "approved", "contacted", "opened", "replied", "meeting",
  "won", "lost", "suppressed",
];

const ALL_QUALITY_LEVELS: LeadQuality[] = ["high", "medium", "low", "unknown"];

const ALL_SIGNAL_TYPES: SignalType[] = [
  "no_website", "instagram_only", "outdated_website", "no_custom_domain",
  "no_visible_email", "no_ssl", "weak_seo", "no_mobile_friendly", "slow_load",
  "has_website", "has_custom_domain", "website_error",
];

describe("STATUS_CONFIG", () => {
  it("has an entry for every LeadStatus value", () => {
    for (const status of ALL_LEAD_STATUSES) {
      expect(STATUS_CONFIG).toHaveProperty(status);
    }
  });

  it("each entry has label, color, and bg fields", () => {
    for (const status of ALL_LEAD_STATUSES) {
      const entry = STATUS_CONFIG[status];
      expect(entry).toHaveProperty("label");
      expect(entry).toHaveProperty("color");
      expect(entry).toHaveProperty("bg");
      expect(typeof entry.label).toBe("string");
      expect(entry.label.length).toBeGreaterThan(0);
    }
  });

  it("new status has label 'Nuevo'", () => {
    expect(STATUS_CONFIG.new.label).toBe("Nuevo");
  });

  it("won status has label 'Ganado'", () => {
    expect(STATUS_CONFIG.won.label).toBe("Ganado");
  });

  it("lost status has label 'Perdido'", () => {
    expect(STATUS_CONFIG.lost.label).toBe("Perdido");
  });
});

describe("QUALITY_CONFIG", () => {
  it("has an entry for every LeadQuality value", () => {
    for (const quality of ALL_QUALITY_LEVELS) {
      expect(QUALITY_CONFIG).toHaveProperty(quality);
    }
  });

  it("each entry has label, color, bg, and dot fields", () => {
    for (const quality of ALL_QUALITY_LEVELS) {
      const entry = QUALITY_CONFIG[quality];
      expect(entry).toHaveProperty("label");
      expect(entry).toHaveProperty("color");
      expect(entry).toHaveProperty("bg");
      expect(entry).toHaveProperty("dot");
      expect(typeof entry.label).toBe("string");
      expect(entry.label.length).toBeGreaterThan(0);
    }
  });

  it("high quality has label 'Alto'", () => {
    expect(QUALITY_CONFIG.high.label).toBe("Alto");
  });

  it("unknown quality has label 'Sin evaluar'", () => {
    expect(QUALITY_CONFIG.unknown.label).toBe("Sin evaluar");
  });
});

describe("SIGNAL_CONFIG", () => {
  it("has an entry for every SignalType value", () => {
    for (const signal of ALL_SIGNAL_TYPES) {
      expect(SIGNAL_CONFIG).toHaveProperty(signal);
    }
  });

  it("each entry has label, emoji, and severity fields", () => {
    for (const signal of ALL_SIGNAL_TYPES) {
      const entry = SIGNAL_CONFIG[signal];
      expect(entry).toHaveProperty("label");
      expect(entry).toHaveProperty("emoji");
      expect(entry).toHaveProperty("severity");
      expect(typeof entry.label).toBe("string");
      expect(["positive", "negative", "neutral"]).toContain(entry.severity);
    }
  });

  it("no_website signal has positive severity", () => {
    expect(SIGNAL_CONFIG.no_website.severity).toBe("positive");
  });

  it("has_website signal has negative severity", () => {
    expect(SIGNAL_CONFIG.has_website.severity).toBe("negative");
  });

  it("website_error signal has neutral severity", () => {
    expect(SIGNAL_CONFIG.website_error.severity).toBe("neutral");
  });
});

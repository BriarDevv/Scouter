"use client";

import { useEffect, useState } from "react";
import { AlertCircle } from "lucide-react";
import { getCorrectionsSummary } from "@/lib/api/client";
import type { ReviewCorrectionSummary } from "@/types";

const CATEGORY_LABELS: Record<string, string> = {
  tone: "Tono",
  cta: "CTA",
  personalization: "Personalizacion",
  length: "Largo",
  accuracy: "Precision",
  relevance: "Relevancia",
  format: "Formato",
  language: "Idioma",
};

const CATEGORY_COLORS: Record<string, string> = {
  tone: "bg-muted dark:bg-muted text-foreground dark:text-foreground",
  cta: "bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200",
  personalization: "bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-200",
  length: "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-800 dark:text-emerald-200",
  accuracy: "bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200",
  relevance: "bg-cyan-100 dark:bg-cyan-900/30 text-cyan-800 dark:text-cyan-200",
  format: "bg-gray-100 dark:bg-gray-800/30 text-gray-800 dark:text-gray-200",
  language: "bg-pink-100 dark:bg-pink-900/30 text-pink-800 dark:text-pink-200",
};

export function TopCorrections() {
  const [corrections, setCorrections] = useState<ReviewCorrectionSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await getCorrectionsSummary(7);
        setCorrections(data.slice(0, 5));
      } catch (err) {
        console.error("top_corrections_fetch_failed", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-center gap-2 mb-3">
        <AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
        <h3 className="text-sm font-medium">Top Correcciones (7 dias)</h3>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Cargando...</p>
      ) : corrections.length === 0 ? (
        <p className="text-sm text-muted-foreground">Sin correcciones registradas.</p>
      ) : (
        <div className="space-y-2">
          {corrections.map((c) => (
            <div key={c.category} className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full shrink-0 ${CATEGORY_COLORS[c.category] || "bg-gray-100 text-gray-800"}`}>
                  {CATEGORY_LABELS[c.category] || c.category}
                </span>
                {c.recent_examples[0] && (
                  <span className="text-xs text-muted-foreground truncate">
                    {c.recent_examples[0]}
                  </span>
                )}
              </div>
              <span className="text-sm font-semibold text-foreground shrink-0">
                {c.count}x
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

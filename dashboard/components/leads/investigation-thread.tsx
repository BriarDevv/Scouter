"use client";

import { useState } from "react";
import { Search, Globe, Clock, ChevronDown, ChevronRight } from "lucide-react";
import type { InvestigationThread } from "@/types";

interface InvestigationThreadViewProps {
  investigation: InvestigationThread;
}

export function InvestigationThreadView({ investigation }: InvestigationThreadViewProps) {
  const [expanded, setExpanded] = useState(false);

  const findings = investigation.findings || {};
  const opportunity = (findings.opportunity as string) || "";
  const pagesCount = investigation.pages_visited?.length || 0;
  const durationSec = (investigation.duration_ms / 1000).toFixed(1);

  return (
    <div className="rounded-xl border border-cyan-100 dark:border-cyan-900/30 bg-cyan-50/40 dark:bg-cyan-950/20 p-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Search className="h-4 w-4 text-cyan-700 dark:text-cyan-300" />
          <p className="text-xs font-medium text-cyan-700 dark:text-cyan-300">
            Scout (Executor 9b)
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>{pagesCount} paginas</span>
          <span>{investigation.loops_used} loops</span>
          <span>{durationSec}s</span>
        </div>
      </div>

      {opportunity && (
        <p className="mt-2 text-sm text-foreground/80">{opportunity}</p>
      )}

      {/* Key findings */}
      {Boolean(findings.key_findings) && Array.isArray(findings.key_findings) && (
        <div className="mt-2 flex flex-wrap gap-1">
          {(findings.key_findings as string[]).slice(0, 5).map((f, i) => (
            <span key={i} className="text-xs bg-cyan-100 dark:bg-cyan-900/30 text-cyan-800 dark:text-cyan-200 rounded px-2 py-0.5">
              {f}
            </span>
          ))}
        </div>
      )}

      {/* Expandable tool calls */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="mt-2 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        {investigation.tool_calls?.length || 0} tool calls
      </button>

      {expanded && investigation.tool_calls && (
        <div className="mt-2 space-y-1.5 max-h-64 overflow-y-auto">
          {investigation.tool_calls.map((tc, i) => (
            <div key={i} className="flex items-start gap-2 text-xs">
              <div className="flex items-center gap-1 min-w-0">
                <Globe className="h-3 w-3 text-muted-foreground shrink-0" />
                <span className="font-medium text-foreground truncate">{tc.name}</span>
              </div>
              <span className="text-muted-foreground shrink-0">
                {tc.duration_ms}ms
              </span>
              {Boolean(tc.arguments?.url) && (
                <span className="text-muted-foreground truncate">
                  {String(tc.arguments.url).slice(0, 50)}
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      {investigation.error && (
        <p className="mt-2 text-xs text-red-600 dark:text-red-400">{investigation.error}</p>
      )}
    </div>
  );
}

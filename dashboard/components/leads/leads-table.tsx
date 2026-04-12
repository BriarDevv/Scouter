"use client";

import { useState, useMemo, useRef, useEffect, useCallback } from "react";
import Link from "next/link";
import { sileo } from "sileo";
import { runFullPipeline, runEnrichment, runScoring, runAnalysis, generateDraft } from "@/lib/api/client";
import { listBriefs } from "@/lib/api/research";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { StatusBadge, ScoreBadge } from "@/components/shared/status-badge";
import { RelativeTime } from "@/components/shared/relative-time";
import { extractDomain, truncate } from "@/lib/formatters";
import type { Lead, LeadStatus, CommercialBrief } from "@/types";
import { STATUS_CONFIG } from "@/lib/constants";
import {
  Search,
  MoreHorizontal,
  ExternalLink,
  RefreshCw,
  Mail,
  Phone,
  ShieldOff,
  ChevronUp,
  ChevronDown,
  Zap,
  Target,
  FileSearch,
  FileText,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface LeadsTableProps {
  leads: Lead[];
}

type SortField = "score" | "created_at" | "business_name";
type SortDir = "asc" | "desc";

const STATUS_FILTERS: (LeadStatus | "all")[] = [
  "all", "new", "enriched", "scored", "qualified", "draft_ready",
  "approved", "contacted", "replied", "meeting", "won", "lost",
];

function SortIcon({
  field,
  sortBy,
  sortDir,
}: {
  field: SortField;
  sortBy: SortField;
  sortDir: SortDir;
}) {
  if (sortBy !== field) return <ChevronDown className="h-3 w-3 opacity-30" />;
  return sortDir === "desc" ? (
    <ChevronDown className="h-3 w-3" />
  ) : (
    <ChevronUp className="h-3 w-3" />
  );
}

const BUDGET_LABELS: Record<string, string> = {
  low: "Bajo", medium: "Medio", high: "Alto", premium: "Premium",
};
const SCOPE_LABELS: Record<string, string> = {
  landing: "Landing", institutional_web: "Web institucional", catalog: "Catálogo",
  ecommerce: "E-commerce", redesign: "Rediseño", automation: "Automatización",
  branding_web: "Branding + Web",
};
const PRIORITY_LABELS: Record<string, string> = {
  immediate: "Inmediata", high: "Alta", normal: "Normal", low: "Baja",
};
const CONTACT_LABELS: Record<string, string> = {
  whatsapp: "WhatsApp", email: "Email", call: "Llamada",
  demo_first: "Demo primero", manual_review: "Revisión manual",
};

export function LeadsTable({ leads }: LeadsTableProps) {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<LeadStatus | "all">("all");
  const [filterOpen, setFilterOpen] = useState(false);
  const filterRef = useRef<HTMLDivElement>(null);
  const [briefView, setBriefView] = useState(false);
  const [briefsMap, setBriefsMap] = useState<Map<string, CommercialBrief>>(new Map());
  const [briefsLoading, setBriefsLoading] = useState(false);

  const toggleBriefView = useCallback(async () => {
    if (!briefView && briefsMap.size === 0) {
      setBriefsLoading(true);
      try {
        const briefs = await listBriefs({ limit: 500 });
        const map = new Map<string, CommercialBrief>();
        for (const b of briefs) map.set(b.lead_id, b);
        setBriefsMap(map);
      } catch {
        // silently fail — brief columns will show "—"
      } finally {
        setBriefsLoading(false);
      }
    }
    setBriefView((v) => !v);
  }, [briefView, briefsMap.size]);

  useEffect(() => {
    if (!filterOpen) return;
    function handleClickOutside(e: MouseEvent) {
      if (filterRef.current && !filterRef.current.contains(e.target as Node)) {
        setFilterOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [filterOpen]);
  const [sortBy, setSortBy] = useState<SortField>("score");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const filtered = useMemo(() => {
    let result = leads;

    if (search) {
      const q = search.toLowerCase();
      result = result.filter(
        (l) =>
          l.business_name.toLowerCase().includes(q) ||
          l.industry?.toLowerCase().includes(q) ||
          l.city?.toLowerCase().includes(q) ||
          l.email?.toLowerCase().includes(q)
      );
    }

    if (statusFilter !== "all") {
      result = result.filter((l) => l.status === statusFilter);
    }

    result = [...result].sort((a, b) => {
      let cmp = 0;
      if (sortBy === "score") cmp = (a.score ?? 0) - (b.score ?? 0);
      else if (sortBy === "business_name") cmp = a.business_name.localeCompare(b.business_name);
      else cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      return sortDir === "desc" ? -cmp : cmp;
    });

    return result;
  }, [leads, search, statusFilter, sortBy, sortDir]);

  function toggleSort(field: SortField) {
    if (sortBy === field) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortBy(field); setSortDir("desc"); }
  }

  return (
    <div className="space-y-3">
      {/* Toolbar */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Buscar..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 h-8 rounded-lg text-xs border-border"
          />
        </div>

        <button
          onClick={toggleBriefView}
          disabled={briefsLoading}
          className={cn(
            "flex h-8 items-center gap-1.5 rounded-lg border px-3 text-xs font-medium transition-colors cursor-pointer outline-none",
            briefView
              ? "border-foreground/20 bg-foreground text-background"
              : "border-border bg-card text-muted-foreground hover:bg-muted hover:text-foreground"
          )}
        >
          <FileText className="h-3.5 w-3.5" />
          Brief
        </button>

        <div className="relative" ref={filterRef}>
          <button
            onClick={() => setFilterOpen(!filterOpen)}
            className="flex h-8 items-center gap-6 rounded-lg border border-border bg-card pl-3 pr-4 text-xs font-medium text-foreground cursor-pointer hover:bg-muted transition-colors outline-none"
          >
            {statusFilter === "all" ? "Todos" : STATUS_CONFIG[statusFilter].label}
            <ChevronDown className={cn("h-3 w-3 text-muted-foreground transition-transform", filterOpen && "rotate-180")} />
          </button>
          {filterOpen && (
            <div className="absolute right-0 top-full mt-1 z-50 min-w-full rounded-xl border border-border bg-card shadow-md overflow-hidden max-h-72 overflow-y-auto">
              {STATUS_FILTERS.map((s) => (
                <button
                  key={s}
                  onClick={() => { setStatusFilter(s); setFilterOpen(false); }}
                  className={cn(
                    "block w-full text-left px-3 py-2.5 text-xs transition-colors",
                    statusFilter === s
                      ? "bg-muted font-semibold text-foreground"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  )}
                >
                  {s === "all" ? "Todos" : STATUS_CONFIG[s].label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="rounded-2xl border border-border bg-card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left px-4 py-2.5 w-[18%]">
                <button onClick={() => toggleSort("business_name")} className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors">
                  Negocio <SortIcon field="business_name" sortBy={sortBy} sortDir={sortDir} />
                </button>
              </th>
              {briefView ? (
                <>
                  <th className="text-left px-3 py-2.5 w-[8%]">
                    <button onClick={() => toggleSort("score")} className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors">
                      Score <SortIcon field="score" sortBy={sortBy} sortDir={sortDir} />
                    </button>
                  </th>
                  <th className="text-left px-3 py-2.5 w-[10%] text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Budget</th>
                  <th className="text-left px-3 py-2.5 w-[16%] text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Rango USD</th>
                  <th className="text-left px-3 py-2.5 w-[14%] text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Scope</th>
                  <th className="text-left px-3 py-2.5 w-[10%] text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Prioridad</th>
                  <th className="text-left px-3 py-2.5 w-[12%] text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Contacto rec.</th>
                  <th className="text-left px-3 py-2.5 w-[8%] text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Estado</th>
                </>
              ) : (
                <>
                  <th className="text-left px-3 py-2.5 w-[12%] text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Rubro</th>
                  <th className="text-left px-3 py-2.5 w-[18%] text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Contacto</th>
                  <th className="text-left px-3 py-2.5 w-[6%]">
                    <button onClick={() => toggleSort("score")} className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors">
                      Score <SortIcon field="score" sortBy={sortBy} sortDir={sortDir} />
                    </button>
                  </th>
                  <th className="text-left px-3 py-2.5 w-[14%] text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Web</th>
                  <th className="text-left px-3 py-2.5 w-[10%] text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Estado</th>
                  <th className="text-left px-3 py-2.5 w-[8%] text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Ciudad</th>
                  <th className="text-left px-3 py-2.5 w-[10%]">
                    <button onClick={() => toggleSort("created_at")} className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors">
                      Fecha <SortIcon field="created_at" sortBy={sortBy} sortDir={sortDir} />
                    </button>
                  </th>
                </>
              )}
              <th className="w-[4%] px-2" />
            </tr>
          </thead>
          <tbody>
            {filtered.map((lead) => {
              const brief = briefsMap.get(lead.id);
              return (
              <tr
                key={lead.id}
                className="border-b border-border/40 last:border-0 hover:bg-muted/40 transition-colors"
              >
                <td className="px-4 py-2.5">
                  <Link href={`/leads/${lead.id}`} className="group min-w-0 block">
                    <p className="text-xs font-medium text-foreground truncate underline decoration-transparent underline-offset-2 group-hover:decoration-foreground/30 transition-all">
                      {truncate(lead.business_name, 32)}
                    </p>
                  </Link>
                </td>
                {briefView ? (
                  <>
                    <td className="px-3 py-2.5"><ScoreBadge score={brief?.opportunity_score ?? lead.score} /></td>
                    <td className="px-3 py-2.5 text-xs text-muted-foreground">
                      {brief?.budget_tier ? BUDGET_LABELS[brief.budget_tier] ?? brief.budget_tier : "—"}
                    </td>
                    <td className="px-3 py-2.5 text-[10px] font-data text-muted-foreground">
                      {brief?.estimated_budget_min != null && brief?.estimated_budget_max != null
                        ? `$${brief.estimated_budget_min.toLocaleString()} – $${brief.estimated_budget_max.toLocaleString()}`
                        : "—"}
                    </td>
                    <td className="px-3 py-2.5 text-xs text-muted-foreground">
                      {brief?.estimated_scope ? SCOPE_LABELS[brief.estimated_scope] ?? brief.estimated_scope : "—"}
                    </td>
                    <td className="px-3 py-2.5 text-xs text-muted-foreground">
                      {brief?.contact_priority ? PRIORITY_LABELS[brief.contact_priority] ?? brief.contact_priority : "—"}
                    </td>
                    <td className="px-3 py-2.5 text-xs text-muted-foreground">
                      {brief?.recommended_contact_method ? CONTACT_LABELS[brief.recommended_contact_method] ?? brief.recommended_contact_method : "—"}
                    </td>
                    <td className="px-3 py-2.5"><StatusBadge status={lead.status} /></td>
                  </>
                ) : (
                  <>
                    <td className="px-3 py-2.5 text-xs text-muted-foreground">{lead.industry || "—"}</td>
                    <td className="px-3 py-2.5">
                      <div className="space-y-0.5">
                        {lead.email && (
                          <div className="flex items-center gap-1 text-[10px] text-muted-foreground font-data truncate">
                            <Mail className="h-2.5 w-2.5 shrink-0" />
                            <span className="truncate">{lead.email}</span>
                          </div>
                        )}
                        {lead.phone && (
                          <div className="flex items-center gap-1 text-[10px] font-data text-muted-foreground truncate">
                            <Phone className="h-2.5 w-2.5 shrink-0" />
                            <span className="truncate">{lead.phone}</span>
                          </div>
                        )}
                        {!lead.email && !lead.phone && (
                          <span className="text-[10px] text-muted-foreground/40">—</span>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-2.5"><ScoreBadge score={lead.score} /></td>
                    <td className="px-3 py-2.5">
                      {lead.website_url ? (
                        <a
                          href={lead.website_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[10px] text-muted-foreground font-data truncate block hover:text-foreground underline decoration-border underline-offset-2 hover:decoration-foreground/30 transition-all"
                        >
                          {extractDomain(lead.website_url)}
                        </a>
                      ) : (
                        <span className="text-[10px] text-muted-foreground/40">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2.5"><StatusBadge status={lead.status} /></td>
                    <td className="px-3 py-2.5 text-xs text-muted-foreground">
                      {lead.city ? (
                        <a
                          href={lead.google_maps_url || (lead.latitude && lead.longitude ? `https://www.google.com/maps?q=${lead.latitude},${lead.longitude}` : `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent([lead.business_name, lead.city].filter(Boolean).join(", "))}`)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="hover:text-foreground underline decoration-border underline-offset-2 hover:decoration-foreground/30 transition-all"
                        >
                          {lead.city}
                        </a>
                      ) : "—"}
                    </td>
                    <td className="px-3 py-2.5 text-[10px] text-muted-foreground font-data">
                      <RelativeTime date={lead.created_at} />
                    </td>
                  </>
                )}
                <td className="px-2 py-2.5">
                  <DropdownMenu>
                    <DropdownMenuTrigger render={
                      <button className="flex items-center justify-center h-6 w-6 rounded-lg hover:bg-muted transition-colors outline-none cursor-pointer" />
                    }>
                      <MoreHorizontal className="h-3.5 w-3.5 text-muted-foreground" />
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-auto rounded-xl p-0 ring-0 bg-card border border-border overflow-hidden min-w-48">
                      <DropdownMenuItem render={<Link href={`/leads/${lead.id}`} />} className="rounded-none px-3 py-2.5 text-xs text-muted-foreground focus:bg-muted focus:text-foreground">
                        <ExternalLink className="h-3.5 w-3.5" /> Ver detalle
                      </DropdownMenuItem>
                      <DropdownMenuSeparator className="mx-0 my-0" />
                      <DropdownMenuItem className="rounded-none px-3 py-2.5 text-xs text-muted-foreground focus:bg-muted focus:text-foreground" onClick={() => {
                        void sileo.promise(runEnrichment(lead.id), {
                          loading: { title: "Enriqueciendo..." },
                          success: { title: "Enriquecimiento iniciado" },
                          error: (err: unknown) => ({ title: "Error", description: err instanceof Error ? err.message : "" }),
                        });
                      }}>
                        <Zap className="h-3.5 w-3.5" /> Enriquecer
                      </DropdownMenuItem>
                      <DropdownMenuItem className="rounded-none px-3 py-2.5 text-xs text-muted-foreground focus:bg-muted focus:text-foreground" onClick={() => {
                        void sileo.promise(runScoring(lead.id), {
                          loading: { title: "Puntuando..." },
                          success: { title: "Puntuación iniciada" },
                          error: (err: unknown) => ({ title: "Error", description: err instanceof Error ? err.message : "" }),
                        });
                      }}>
                        <Target className="h-3.5 w-3.5" /> Puntuar
                      </DropdownMenuItem>
                      <DropdownMenuItem className="rounded-none px-3 py-2.5 text-xs text-muted-foreground focus:bg-muted focus:text-foreground" onClick={() => {
                        void sileo.promise(runAnalysis(lead.id), {
                          loading: { title: "Analizando..." },
                          success: { title: "Análisis iniciado" },
                          error: (err: unknown) => ({ title: "Error", description: err instanceof Error ? err.message : "" }),
                        });
                      }}>
                        <FileSearch className="h-3.5 w-3.5" /> Analizar
                      </DropdownMenuItem>
                      <DropdownMenuItem className="rounded-none px-3 py-2.5 text-xs text-muted-foreground focus:bg-muted focus:text-foreground" onClick={() => {
                        void sileo.promise(runFullPipeline(lead.id), {
                          loading: { title: "Ejecutando pipeline..." },
                          success: { title: "Pipeline iniciado" },
                          error: (err: unknown) => ({ title: "Error", description: err instanceof Error ? err.message : "" }),
                        });
                      }}>
                        <RefreshCw className="h-3.5 w-3.5" /> Pipeline completo
                      </DropdownMenuItem>
                      {lead.email && (
                        <>
                          <DropdownMenuSeparator className="mx-0 my-0" />
                          <DropdownMenuItem className="rounded-none px-3 py-2.5 text-xs text-muted-foreground focus:bg-muted focus:text-foreground" onClick={() => {
                            void sileo.promise(generateDraft(lead.id, "email"), {
                              loading: { title: "Generando draft..." },
                              success: { title: "Draft generado" },
                              error: (err: unknown) => ({ title: "Error", description: err instanceof Error ? err.message : "" }),
                            });
                          }}>
                            <Mail className="h-3.5 w-3.5" /> Generar draft
                          </DropdownMenuItem>
                        </>
                      )}
                      <DropdownMenuSeparator className="mx-0 my-0" />
                      <DropdownMenuItem className="rounded-none px-3 py-2.5 text-xs text-red-600 focus:bg-red-50 dark:focus:bg-red-950/20 focus:text-red-600">
                        <ShieldOff className="h-3.5 w-3.5" /> Suprimir
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </td>
              </tr>
              );
            })}
          </tbody>
        </table>

        {/* Footer */}
        <div className="flex items-center border-t border-border px-4 py-2.5">
          <span className="text-[10px] text-muted-foreground">
            <span className="font-data font-bold">{filtered.length}</span> leads
            {statusFilter !== "all" && ` · ${STATUS_CONFIG[statusFilter].label}`}
          </span>
        </div>
      </div>
    </div>
  );
}

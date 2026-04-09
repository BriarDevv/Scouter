"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { sileo } from "sileo";
import { runFullPipeline, generateDraft } from "@/lib/api/client";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { StatusBadge, ScoreBadge } from "@/components/shared/status-badge";
import { RelativeTime } from "@/components/shared/relative-time";
import { truncate } from "@/lib/formatters";
import type { Lead, LeadStatus } from "@/types";
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
} from "lucide-react";
import { cn } from "@/lib/utils";

interface LeadsTableProps {
  leads: Lead[];
}

const STATUS_FILTERS: (LeadStatus | "all")[] = [
  "all", "new", "enriched", "scored", "qualified", "draft_ready",
  "approved", "contacted", "replied", "meeting", "won", "lost",
];

export function LeadsTable({ leads }: LeadsTableProps) {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<LeadStatus | "all">("all");
  const [sortBy, setSortBy] = useState<"score" | "created_at" | "business_name">("score");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

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

  function toggleSort(field: typeof sortBy) {
    if (sortBy === field) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortBy(field); setSortDir("desc"); }
  }

  const SortIcon = ({ field }: { field: typeof sortBy }) => {
    if (sortBy !== field) return <ChevronDown className="h-3 w-3 opacity-30" />;
    return sortDir === "desc" ? <ChevronDown className="h-3 w-3" /> : <ChevronUp className="h-3 w-3" />;
  };

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
            className="pl-9 h-8 rounded-lg text-xs"
          />
        </div>

        <div className="flex items-center gap-1 overflow-x-auto">
          {STATUS_FILTERS.map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={cn(
                "shrink-0 rounded-lg px-2 py-1 text-[10px] font-medium transition-colors",
                statusFilter === s
                  ? "bg-foreground text-background"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              {s === "all" ? "Todos" : STATUS_CONFIG[s].label}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="rounded-2xl border border-border bg-card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left px-4 py-2.5 w-[260px]">
                <button onClick={() => toggleSort("business_name")} className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors">
                  Negocio <SortIcon field="business_name" />
                </button>
              </th>
              <th className="text-left px-3 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Contacto</th>
              <th className="text-left px-3 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Rubro</th>
              <th className="text-left px-3 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Ciudad</th>
              <th className="text-left px-3 py-2.5">
                <button onClick={() => toggleSort("score")} className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors">
                  Score <SortIcon field="score" />
                </button>
              </th>
              <th className="text-left px-3 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Estado</th>
              <th className="text-left px-3 py-2.5">
                <button onClick={() => toggleSort("created_at")} className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors">
                  Fecha <SortIcon field="created_at" />
                </button>
              </th>
              <th className="w-10 px-2" />
            </tr>
          </thead>
          <tbody>
            {filtered.map((lead) => (
              <tr
                key={lead.id}
                className="border-b border-border/40 last:border-0 hover:bg-muted/40 transition-colors"
              >
                <td className="px-4 py-2.5">
                  <Link href={`/leads/${lead.id}`} className="group min-w-0 block">
                    <p className="text-xs font-medium text-foreground truncate group-hover:underline">
                      {truncate(lead.business_name, 32)}
                    </p>
                  </Link>
                </td>
                <td className="px-3 py-2.5">
                  <div className="space-y-0.5">
                    {lead.email && (
                      <div className="flex items-center gap-1 text-[10px] text-muted-foreground font-data truncate">
                        <Mail className="h-2.5 w-2.5 shrink-0" />
                        <span className="truncate">{lead.email}</span>
                      </div>
                    )}
                    {lead.phone && (
                      <div className="flex items-center gap-1 text-[10px] font-data text-emerald-600 dark:text-emerald-400">
                        <Phone className="h-2.5 w-2.5 shrink-0" />
                        {lead.phone}
                      </div>
                    )}
                    {!lead.email && !lead.phone && (
                      <span className="text-[10px] text-muted-foreground/40">—</span>
                    )}
                  </div>
                </td>
                <td className="px-3 py-2.5 text-xs text-muted-foreground">{lead.industry || "—"}</td>
                <td className="px-3 py-2.5 text-xs text-muted-foreground">{lead.city || "—"}</td>
                <td className="px-3 py-2.5"><ScoreBadge score={lead.score} /></td>
                <td className="px-3 py-2.5"><StatusBadge status={lead.status} /></td>
                <td className="px-3 py-2.5 text-[10px] text-muted-foreground font-data">
                  <RelativeTime date={lead.created_at} />
                </td>
                <td className="px-2 py-2.5">
                  <DropdownMenu>
                    <DropdownMenuTrigger render={<Button variant="ghost" size="icon-xs" className="h-6 w-6" />}>
                      <MoreHorizontal className="h-3.5 w-3.5 text-muted-foreground" />
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-44">
                      <DropdownMenuItem render={<Link href={`/leads/${lead.id}`} />}>
                        <ExternalLink className="mr-2 h-3.5 w-3.5" /> Ver detalle
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => {
                        void sileo.promise(runFullPipeline(lead.id), {
                          loading: { title: "Ejecutando pipeline..." },
                          success: { title: "Pipeline iniciado" },
                          error: (err: unknown) => ({ title: "Error", description: err instanceof Error ? err.message : "" }),
                        });
                      }}><RefreshCw className="mr-2 h-3.5 w-3.5" /> Pipeline</DropdownMenuItem>
                      <DropdownMenuItem onClick={() => {
                        void sileo.promise(generateDraft(lead.id), {
                          loading: { title: "Generando draft..." },
                          success: { title: "Draft generado" },
                          error: (err: unknown) => ({ title: "Error", description: err instanceof Error ? err.message : "" }),
                        });
                      }}><Mail className="mr-2 h-3.5 w-3.5" /> Generar draft</DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem className="text-red-600"><ShieldOff className="mr-2 h-3.5 w-3.5" /> Suprimir</DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </td>
              </tr>
            ))}
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

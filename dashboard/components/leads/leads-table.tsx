"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { StatusBadge, QualityBadge, ScoreBadge } from "@/components/shared/status-badge";
import { RelativeTime } from "@/components/shared/relative-time";
import { extractDomain, truncate } from "@/lib/formatters";
import type { Lead, LeadStatus } from "@/types";
import { STATUS_CONFIG } from "@/lib/constants";
import {
  Search,
  SlidersHorizontal,
  MoreHorizontal,
  ExternalLink,
  RefreshCw,
  Mail,
  ShieldOff,
  ChevronLeft,
  ChevronRight,
  ArrowUpDown,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface LeadsTableProps {
  leads: Lead[];
}

const PAGE_SIZE = 10;

const QUICK_FILTER_OPTIONS: (LeadStatus | "all")[] = [
  "all", "qualified", "contacted", "replied",
];

const MORE_FILTER_OPTIONS: LeadStatus[] = [
  "new", "enriched", "scored", "draft_ready",
  "approved", "opened", "meeting", "won", "lost", "suppressed",
];

export function LeadsTable({ leads }: LeadsTableProps) {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<LeadStatus | "all">("all");
  const [sortBy, setSortBy] = useState<"score" | "created_at" | "business_name">("created_at");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);

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

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  function toggleSort(field: typeof sortBy) {
    if (sortBy === field) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortBy(field); setSortDir("desc"); }
  }

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[240px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Buscar por nombre, rubro, ciudad, email..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="pl-9 h-9 rounded-xl border-border bg-card text-sm"
          />
        </div>

        <div className="flex items-center gap-1.5">
          {QUICK_FILTER_OPTIONS.map((s) => (
            <button
              key={s}
              onClick={() => { setStatusFilter(s); setPage(1); }}
              className={cn(
                "shrink-0 rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors",
                statusFilter === s
                  ? "bg-violet-100 dark:bg-violet-950/40 text-violet-700 dark:text-violet-300"
                  : "bg-card text-muted-foreground hover:bg-muted hover:text-foreground/80 border border-border"
              )}
            >
              {s === "all" ? "Todos" : STATUS_CONFIG[s].label}
            </button>
          ))}
          <select
            value={MORE_FILTER_OPTIONS.includes(statusFilter as LeadStatus) ? statusFilter : ""}
            onChange={(e) => {
              const val = e.target.value as LeadStatus;
              if (val) { setStatusFilter(val); setPage(1); }
            }}
            className={cn(
              "rounded-lg px-2.5 py-1.5 text-xs font-medium border transition-colors bg-card text-muted-foreground cursor-pointer",
              MORE_FILTER_OPTIONS.includes(statusFilter as LeadStatus)
                ? "border-violet-200 bg-violet-100 dark:bg-violet-950/40 text-violet-700 dark:text-violet-300"
                : "border-border hover:bg-muted"
            )}
          >
            <option value="">Más filtros</option>
            {MORE_FILTER_OPTIONS.map((s) => (
              <option key={s} value={s}>{STATUS_CONFIG[s].label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-2xl border border-border bg-card shadow-sm overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent border-border">
              <TableHead className="w-[250px]">
                <button onClick={() => toggleSort("business_name")} className="flex items-center gap-1 text-xs font-medium font-heading">
                  Negocio <ArrowUpDown className="h-3 w-3" />
                </button>
              </TableHead>
              <TableHead className="text-xs font-medium font-heading">Rubro</TableHead>
              <TableHead className="text-xs font-medium font-heading">Ciudad</TableHead>
              <TableHead className="text-xs font-medium font-heading">Web</TableHead>
              <TableHead>
                <button onClick={() => toggleSort("score")} className="flex items-center gap-1 text-xs font-medium font-heading">
                  Score <ArrowUpDown className="h-3 w-3" />
                </button>
              </TableHead>
              <TableHead className="text-xs font-medium font-heading">Calidad</TableHead>
              <TableHead className="text-xs font-medium font-heading">Estado</TableHead>
              <TableHead>
                <button onClick={() => toggleSort("created_at")} className="flex items-center gap-1 text-xs font-medium font-heading">
                  Creado <ArrowUpDown className="h-3 w-3" />
                </button>
              </TableHead>
              <TableHead className="w-10" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {paginated.map((lead) => (
              <TableRow key={lead.id} className="border-border/50 hover:bg-muted/50 transition-colors">
                <TableCell>
                  <Link href={`/leads/${lead.id}`} className="group flex items-center gap-2">
                    <span className="font-medium text-foreground group-hover:text-violet-700 transition-colors">
                      {truncate(lead.business_name, 30)}
                    </span>
                  </Link>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">{lead.industry || "—"}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{lead.city || "—"}</TableCell>
                <TableCell>
                  {lead.website_url ? (
                    <span className="text-xs text-muted-foreground font-data">{extractDomain(lead.website_url)}</span>
                  ) : (
                    <span className="text-xs text-muted-foreground">Sin web</span>
                  )}
                </TableCell>
                <TableCell><ScoreBadge score={lead.score} /></TableCell>
                <TableCell><QualityBadge quality={lead.quality} /></TableCell>
                <TableCell><StatusBadge status={lead.status} /></TableCell>
                <TableCell className="text-xs text-muted-foreground font-data">
                  <RelativeTime date={lead.created_at} />
                </TableCell>
                <TableCell>
                  <DropdownMenu>
                    <DropdownMenuTrigger render={<Button variant="ghost" size="icon" className="h-8 w-8" />}>
                      <MoreHorizontal className="h-4 w-4 text-muted-foreground" />
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-48">
                      <DropdownMenuItem render={<Link href={`/leads/${lead.id}`} />}>
                        <ExternalLink className="mr-2 h-3.5 w-3.5" /> Ver detalle
                      </DropdownMenuItem>
                      <DropdownMenuItem><RefreshCw className="mr-2 h-3.5 w-3.5" /> Ejecutar pipeline</DropdownMenuItem>
                      <DropdownMenuItem><Mail className="mr-2 h-3.5 w-3.5" /> Generar draft</DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem className="text-red-600"><ShieldOff className="mr-2 h-3.5 w-3.5" /> Suprimir</DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>

        {/* Pagination */}
        <div className="flex items-center justify-between border-t border-border px-4 py-3">
          <span className="text-xs text-muted-foreground">
            <span className="font-data">{filtered.length}</span> leads{statusFilter !== "all" && ` (${STATUS_CONFIG[statusFilter].label})`}
          </span>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="px-2 text-xs text-muted-foreground font-data">
              {page} / {totalPages || 1}
            </span>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

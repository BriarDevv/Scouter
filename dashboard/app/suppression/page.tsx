"use client";

import { useState } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { formatDate } from "@/lib/formatters";
import { MOCK_SUPPRESSION } from "@/data/mock";
import { ShieldOff, Plus, Search, Undo2 } from "lucide-react";
import { EmptyState } from "@/components/shared/empty-state";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogClose,
} from "@/components/ui/dialog";

export default function SuppressionPage() {
  const [search, setSearch] = useState("");
  const [items, setItems] = useState(MOCK_SUPPRESSION);

  const filtered = search
    ? items.filter(
        (s) =>
          s.email?.toLowerCase().includes(search.toLowerCase()) ||
          s.domain?.toLowerCase().includes(search.toLowerCase()) ||
          s.business_name?.toLowerCase().includes(search.toLowerCase())
      )
    : items;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Lista de Supresión"
        description="Emails, dominios y teléfonos que no deben ser contactados"
      >
        <Dialog>
          <DialogTrigger render={<Button className="rounded-xl bg-violet-600 text-white hover:bg-violet-700" />}>
            <Plus className="mr-2 h-4 w-4" />
            Agregar
          </DialogTrigger>
          <DialogContent className="rounded-2xl sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Agregar a Supresión</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div>
                <label className="text-sm font-medium text-slate-700">Email</label>
                <Input placeholder="email@ejemplo.com" className="mt-1 rounded-xl" />
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700">Dominio</label>
                <Input placeholder="ejemplo.com" className="mt-1 rounded-xl" />
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700">Motivo</label>
                <Input placeholder="Ej: pidió no ser contactado" className="mt-1 rounded-xl" />
              </div>
            </div>
            <DialogFooter>
              <DialogClose render={<Button variant="outline" className="rounded-xl" />}>
                Cancelar
              </DialogClose>
              <Button className="rounded-xl bg-violet-600 text-white hover:bg-violet-700">
                Agregar
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </PageHeader>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <Input
          placeholder="Buscar por email, dominio o negocio..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9 h-9 rounded-xl border-slate-200 bg-white text-sm"
        />
      </div>

      {/* Table */}
      {filtered.length > 0 ? (
        <div className="rounded-2xl border border-slate-100 bg-white shadow-sm overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="border-slate-100 hover:bg-transparent">
                <TableHead className="text-xs font-medium font-heading">Email</TableHead>
                <TableHead className="text-xs font-medium font-heading">Dominio</TableHead>
                <TableHead className="text-xs font-medium font-heading">Negocio</TableHead>
                <TableHead className="text-xs font-medium font-heading">Motivo</TableHead>
                <TableHead className="text-xs font-medium font-heading">Fecha</TableHead>
                <TableHead className="w-10" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((entry) => (
                <TableRow key={entry.id} className="border-slate-50 hover:bg-slate-50/50">
                  <TableCell className="text-sm text-slate-900 font-data">{entry.email || "—"}</TableCell>
                  <TableCell className="text-sm text-slate-600 font-data">{entry.domain || "—"}</TableCell>
                  <TableCell className="text-sm text-slate-600">{entry.business_name || "—"}</TableCell>
                  <TableCell className="text-sm text-slate-500">{entry.reason || "—"}</TableCell>
                  <TableCell className="text-sm text-slate-500 font-data">{formatDate(entry.added_at)}</TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-slate-400 hover:text-red-600"
                      title="Restaurar (remover de supresión)"
                    >
                      <Undo2 className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          <div className="border-t border-slate-100 px-4 py-3">
            <span className="text-xs text-slate-500">{filtered.length} entradas</span>
          </div>
        </div>
      ) : (
        <EmptyState
          icon={ShieldOff}
          title="Lista vacía"
          description="No hay entradas en la lista de supresión que coincidan con tu búsqueda."
        />
      )}
    </div>
  );
}

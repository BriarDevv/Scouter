"use client";

import { useState } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogClose,
} from "@/components/ui/dialog";
import { SkeletonTable } from "@/components/shared/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { formatDate } from "@/lib/formatters";
import { usePageData } from "@/lib/hooks/use-page-data";
import { addToSuppression, getSuppressionList, removeFromSuppression } from "@/lib/api/client";
import { ShieldOff, Plus, Search, Trash2 } from "lucide-react";
import { sileo } from "sileo";

export default function SuppressionPage() {
  const [search, setSearch] = useState("");
  const { data: items, loading, refresh } = usePageData(
    () => getSuppressionList(),
  );
  const [localItems, setLocalItems] = useState<typeof items | null>(null);
  const [email, setEmail] = useState("");
  const [domain, setDomain] = useState("");
  const [reason, setReason] = useState("");
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [removingId, setRemovingId] = useState<string | null>(null);
  const [confirmRemoveId, setConfirmRemoveId] = useState<string | null>(null);

  const displayItems = localItems ?? items;

  async function handleAdd() {
    setIsSubmitting(true);
    try {
      await sileo.promise(
        (async () => {
          const entry = await addToSuppression({
            email: email || undefined,
            domain: domain || undefined,
            reason: reason || undefined,
          });
          setLocalItems((current) => [entry, ...(current ?? items ?? [])]);
          setEmail("");
          setDomain("");
          setReason("");
          setIsDialogOpen(false);
        })(),
        {
          loading: { title: "Agregando a supresión..." },
          success: { title: "Agregado a supresión" },
          error: (err: unknown) => ({
            title: "Error al agregar",
            description: err instanceof Error ? err.message : "No se pudo agregar.",
          }),
        }
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleRemove(id: string) {
    setRemovingId(id);
    try {
      await sileo.promise(
        (async () => {
          await removeFromSuppression(id);
          setLocalItems((current) => (current ?? items ?? []).filter((entry) => entry.id !== id));
        })(),
        {
          loading: { title: "Removiendo de supresión..." },
          success: { title: "Removido de supresión" },
          error: (err: unknown) => ({
            title: "Error al remover",
            description: err instanceof Error ? err.message : "No se pudo remover.",
          }),
        }
      );
    } finally {
      setRemovingId(null);
      setConfirmRemoveId(null);
    }
  }

  const filtered = search
    ? (displayItems ?? []).filter(
        (s) =>
          s.email?.toLowerCase().includes(search.toLowerCase()) ||
          s.domain?.toLowerCase().includes(search.toLowerCase()) ||
          s.business_name?.toLowerCase().includes(search.toLowerCase())
      )
    : (displayItems ?? []);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Lista de Supresión"
        description="Emails, dominios y teléfonos que no deben ser contactados"
      >
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
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
                <label className="text-sm font-medium text-foreground/80">Email</label>
                <Input
                  placeholder="email@ejemplo.com"
                  className="mt-1 rounded-xl"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              <div>
                <label className="text-sm font-medium text-foreground/80">Dominio</label>
                <Input
                  placeholder="ejemplo.com"
                  className="mt-1 rounded-xl"
                  value={domain}
                  onChange={(e) => setDomain(e.target.value)}
                />
              </div>
              <div>
                <label className="text-sm font-medium text-foreground/80">Motivo</label>
                <Input
                  placeholder="Ej: pidió no ser contactado"
                  className="mt-1 rounded-xl"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
              </div>
            </div>
            <DialogFooter>
              <DialogClose render={<Button variant="outline" className="rounded-xl" />}>
                Cancelar
              </DialogClose>
              <Button
                className="rounded-xl bg-violet-600 text-white hover:bg-violet-700"
                onClick={() => void handleAdd()}
                disabled={isSubmitting || (!email && !domain)}
              >
                Agregar
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </PageHeader>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Buscar por email, dominio o negocio..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9 h-9 rounded-xl border-border bg-card text-sm"
        />
      </div>

      {/* Confirmation dialog for delete */}
      <Dialog open={!!confirmRemoveId} onOpenChange={(open) => !open && setConfirmRemoveId(null)}>
        <DialogContent className="rounded-2xl sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Confirmar eliminación</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground py-2">
            ¿Estás seguro de que querés remover esta entrada de la lista de supresión?
          </p>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" className="rounded-xl" />}>
              Cancelar
            </DialogClose>
            <Button
              className="rounded-xl bg-red-600 text-white hover:bg-red-700"
              onClick={() => confirmRemoveId && void handleRemove(confirmRemoveId)}
              disabled={removingId === confirmRemoveId}
            >
              Remover
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Table */}
      {loading ? (
        <SkeletonTable rows={5} />
      ) : filtered.length > 0 ? (
        <div className="rounded-2xl border border-border bg-card shadow-sm overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="border-border hover:bg-transparent">
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
                <TableRow key={entry.id} className="border-border/50 hover:bg-muted/50">
                  <TableCell className="text-sm text-foreground font-data">{entry.email || "—"}</TableCell>
                  <TableCell className="text-sm text-muted-foreground font-data">{entry.domain || "—"}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{entry.business_name || "—"}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{entry.reason || "—"}</TableCell>
                  <TableCell className="text-sm text-muted-foreground font-data">{formatDate(entry.added_at)}</TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-muted-foreground hover:text-red-600"
                      title="Remover de la lista"
                      onClick={() => setConfirmRemoveId(entry.id)}
                      disabled={removingId === entry.id}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          <div className="border-t border-border px-4 py-3">
            <span className="text-xs text-muted-foreground">{filtered.length} entradas</span>
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

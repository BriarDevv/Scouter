"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

interface OutreachPaginationProps {
  leadsPage: number;
  leadsTotalPages: number;
  leadsTotal: number;
  onPageChange: (page: number) => void;
}

export function OutreachPagination({
  leadsPage,
  leadsTotalPages,
  leadsTotal,
  onPageChange,
}: OutreachPaginationProps) {
  if (leadsTotalPages <= 1) return null;

  return (
    <div className="flex items-center justify-between border-t border-border pt-4">
      <span className="text-xs text-muted-foreground">
        {leadsTotal} lead{leadsTotal !== 1 ? "s" : ""} · página {leadsPage} / {leadsTotalPages}
      </span>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          className="rounded-xl gap-1.5"
          disabled={leadsPage <= 1}
          onClick={() => onPageChange(leadsPage - 1)}
        >
          <ChevronLeft className="h-3.5 w-3.5" />
          Anterior
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="rounded-xl gap-1.5"
          disabled={leadsPage >= leadsTotalPages}
          onClick={() => onPageChange(leadsPage + 1)}
        >
          Siguiente
          <ChevronRight className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}

"use client";

import { PageHeader } from "@/components/layout/page-header";
import { LeadsTable } from "@/components/leads/leads-table";
import { Button } from "@/components/ui/button";
import { MOCK_LEADS } from "@/data/mock";
import { Plus } from "lucide-react";

export default function LeadsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Leads"
        description="Gestión de leads y pipeline comercial"
      >
        <Button className="rounded-xl bg-violet-600 text-white hover:bg-violet-700">
          <Plus className="mr-2 h-4 w-4" />
          Nuevo Lead
        </Button>
      </PageHeader>

      <LeadsTable leads={MOCK_LEADS} />
    </div>
  );
}

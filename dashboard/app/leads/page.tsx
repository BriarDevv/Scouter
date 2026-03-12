"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { LeadsTable } from "@/components/leads/leads-table";
import { Button } from "@/components/ui/button";
import { MOCK_LEADS } from "@/data/mock";
import { getLeads } from "@/lib/api/client";
import type { Lead } from "@/types";
import { Plus } from "lucide-react";

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>(MOCK_LEADS);

  useEffect(() => {
    let active = true;

    async function loadLeads() {
      const response = await getLeads({ page: 1, page_size: 200 });
      if (!active) {
        return;
      }
      setLeads(response.items);
    }

    void loadLeads();

    return () => {
      active = false;
    };
  }, []);

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

      <LeadsTable leads={leads} />
    </div>
  );
}

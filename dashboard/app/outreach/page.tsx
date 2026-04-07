"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { Skeleton, SkeletonStatCard, SkeletonCard } from "@/components/shared/skeleton";
import {
  getDraftDeliveries,
  getDrafts,
  getInboundMessages,
  getInboundThreads,
  getLeads,
  reviewDraft,
  sendOutreachDraft,
} from "@/lib/api/client";
import type {
  Lead,
  DraftStatus,
  EmailThreadSummary,
  InboundMessage,
  OutreachDelivery,
  OutreachDraft,
} from "@/types";
import { sileo } from "sileo";

import { DraftList } from "@/components/outreach/draft-list";
import { DraftDetail } from "@/components/outreach/draft-detail";
import { OutreachPagination } from "@/components/outreach/send-actions";

const LEADS_PAGE_SIZE = 50;

export default function OutreachPage() {
  const [filter, setFilter] = useState<DraftStatus | "all">("all");
  const [selectedDraft, setSelectedDraft] = useState<OutreachDraft | null>(null);
  const [drafts, setDrafts] = useState<OutreachDraft[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [leadsPage, setLeadsPage] = useState(1);
  const [leadsTotal, setLeadsTotal] = useState(0);
  const [inboundMessages, setInboundMessages] = useState<InboundMessage[]>([]);
  const [inboundThreads, setInboundThreads] = useState<EmailThreadSummary[]>([]);
  const [selectedDeliveries, setSelectedDeliveries] = useState<OutreachDelivery[]>([]);
  const [mailError, setMailError] = useState<string | null>(null);
  const [isReviewingDraftId, setIsReviewingDraftId] = useState<string | null>(null);
  const [isSendingDraftId, setIsSendingDraftId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const leadsTotalPages = Math.max(1, Math.ceil(leadsTotal / LEADS_PAGE_SIZE));

  useEffect(() => {
    let active = true;

    async function loadOutreachData() {
      const [nextDrafts, nextLeads, nextInboundMessages, nextInboundThreads] = await Promise.all([
        getDrafts(),
        getLeads({ page: leadsPage, page_size: LEADS_PAGE_SIZE }),
        getInboundMessages({ limit: 100 }).catch(() => null),
        getInboundThreads({ limit: 50 }).catch(() => null),
      ]);

      if (!active) return;

      setDrafts(nextDrafts);
      setLeads(nextLeads.items);
      setLeadsTotal(nextLeads.total);
      if (nextInboundMessages && nextInboundThreads) {
        setInboundMessages(nextInboundMessages);
        setInboundThreads(nextInboundThreads);
        setMailError(null);
      } else {
        setInboundMessages([]);
        setInboundThreads([]);
        setMailError("No se pudo cargar el contexto de replies inbound.");
      }
      setSelectedDraft((current) =>
        current ? nextDrafts.find((draft) => draft.id === current.id) ?? null : nextDrafts[0] ?? null
      );
      setLoading(false);
    }

    void loadOutreachData();

    return () => {
      active = false;
    };
  }, [leadsPage]);

  useEffect(() => {
    let active = true;

    async function loadSelectedDraftDeliveries() {
      if (!selectedDraft) {
        setSelectedDeliveries([]);
        return;
      }

      try {
        const deliveries = await getDraftDeliveries(selectedDraft.id);
        if (!active) return;
        setSelectedDeliveries(deliveries);
      } catch {
        if (!active) return;
        setSelectedDeliveries([]);
      }
    }

    void loadSelectedDraftDeliveries();

    return () => {
      active = false;
    };
  }, [selectedDraft]);

  const filteredDrafts = filter === "all"
    ? drafts
    : drafts.filter((d) => d.status === filter);
  const selectedReplies = selectedDraft
    ? inboundMessages.filter((message) => message.draft_id === selectedDraft.id)
    : [];
  const selectedThreads = selectedDraft
    ? inboundThreads.filter((thread) => thread.draft_id === selectedDraft.id)
    : [];

  async function handleReview(draftId: string, approved: boolean) {
    setIsReviewingDraftId(draftId);
    try {
      await sileo.promise(
        (async () => {
          const updated = await reviewDraft(draftId, approved);
          setDrafts((current) =>
            current.map((draft) => (draft.id === draftId ? { ...draft, ...updated } : draft))
          );
        })(),
        {
          loading: { title: approved ? "Aprobando draft..." : "Rechazando draft..." },
          success: { title: approved ? "Draft aprobado" : "Draft rechazado" },
          error: (err: unknown) => ({
            title: "Error al revisar",
            description: err instanceof Error ? err.message : "No se pudo revisar el draft.",
          }),
        }
      );
    } finally {
      setIsReviewingDraftId(null);
    }
  }

  async function handleSend(draftId: string) {
    setIsSendingDraftId(draftId);
    try {
      await sileo.promise(
        (async () => {
          await sendOutreachDraft(draftId);
          setDrafts((current) =>
            current.map((draft) => (draft.id === draftId ? { ...draft, status: "sent" as DraftStatus } : draft))
          );
        })(),
        {
          loading: { title: "Enviando mail..." },
          success: { title: "Mail enviado" },
          error: (err: unknown) => ({
            title: "Error al enviar",
            description: err instanceof Error ? err.message : "No se pudo enviar el mail.",
          }),
        }
      );
    } finally {
      setIsSendingDraftId(null);
    }
  }

  if (loading) {
    return (
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[1400px] px-8 py-8">
          <div className="space-y-6">
            <PageHeader title="Outreach" description="Gestión de borradores y actividad comercial" />
            <div className="grid gap-6 lg:grid-cols-3">
              <div className="lg:col-span-2 space-y-4">
                <Skeleton className="h-9 w-full max-w-md" />
                {Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} />)}
              </div>
              <div>
                <SkeletonCard className="h-64" />
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8">
        <div className="space-y-6">
          <PageHeader
            title="Outreach"
            description="Gestión de borradores y actividad comercial"
          />

          <div className="grid gap-6 lg:grid-cols-3">
            <DraftList
              drafts={drafts}
              filteredDrafts={filteredDrafts}
              leads={leads}
              filter={filter}
              onFilterChange={setFilter}
              selectedDraft={selectedDraft}
              onSelectDraft={setSelectedDraft}
              isReviewingDraftId={isReviewingDraftId}
              isSendingDraftId={isSendingDraftId}
              onReview={(draftId, approved) => void handleReview(draftId, approved)}
              onSend={(draftId) => void handleSend(draftId)}
            />

            <DraftDetail
              selectedDraft={selectedDraft}
              selectedDeliveries={selectedDeliveries}
              selectedReplies={selectedReplies}
              selectedThreads={selectedThreads}
              mailError={mailError}
            />
          </div>

          <OutreachPagination
            leadsPage={leadsPage}
            leadsTotalPages={leadsTotalPages}
            leadsTotal={leadsTotal}
            onPageChange={setLeadsPage}
          />
        </div>
      </div>
    </div>
  );
}

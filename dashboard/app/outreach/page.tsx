"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { Skeleton, SkeletonStatCard, SkeletonCard } from "@/components/shared/skeleton";
import {
  getDraftDeliveries,
  reviewDraft,
  sendOutreachDraft,
} from "@/lib/api/client";
import { useApi } from "@/lib/hooks/use-swr-fetch";
import type {
  Lead,
  DraftStatus,
  EmailThreadSummary,
  InboundMessage,
  OutreachDelivery,
  OutreachDraft,
  PaginatedResponse,
} from "@/types";
import { sileo } from "sileo";

import { DraftList } from "@/components/outreach/draft-list";
import { DraftDetail } from "@/components/outreach/draft-detail";
import { OutreachPagination } from "@/components/outreach/send-actions";

const LEADS_PAGE_SIZE = 50;

export default function OutreachPage() {
  const [filter, setFilter] = useState<DraftStatus | "all">("all");
  const [selectedDraft, setSelectedDraft] = useState<OutreachDraft | null>(null);
  const [leadsPage, setLeadsPage] = useState(1);
  const [selectedDeliveries, setSelectedDeliveries] = useState<OutreachDelivery[]>([]);
  const [mailError, setMailError] = useState<string | null>(null);
  const [isReviewingDraftId, setIsReviewingDraftId] = useState<string | null>(null);
  const [isSendingDraftId, setIsSendingDraftId] = useState<string | null>(null);

  const { data: drafts, isLoading: draftsLoading, mutate: mutateDrafts } = useApi<OutreachDraft[]>("/outreach/drafts");
  const { data: leadsResponse } = useApi<PaginatedResponse<Lead>>(
    `/leads?page=${leadsPage}&page_size=${LEADS_PAGE_SIZE}`
  );
  const { data: inboundMessages, error: inboundError } = useApi<InboundMessage[]>("/mail/inbound/messages?limit=100");
  const { data: inboundThreads } = useApi<EmailThreadSummary[]>("/mail/inbound/threads?limit=50");

  const leads = leadsResponse?.items ?? [];
  const leadsTotal = leadsResponse?.total ?? 0;
  const leadsTotalPages = Math.max(1, Math.ceil(leadsTotal / LEADS_PAGE_SIZE));
  const loading = draftsLoading;

  // Set mail error if inbound fetch failed
  useEffect(() => {
    if (inboundError) {
      setMailError("No se pudo cargar el contexto de replies inbound.");
    } else {
      setMailError(null);
    }
  }, [inboundError]);

  // Auto-select first draft when drafts load
  useEffect(() => {
    if (!drafts) return;
    setSelectedDraft((current) =>
      current ? drafts.find((draft) => draft.id === current.id) ?? null : drafts[0] ?? null
    );
  }, [drafts]);

  // Load deliveries when selected draft changes
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
    ? (drafts ?? [])
    : (drafts ?? []).filter((d) => d.status === filter);
  const selectedReplies = selectedDraft
    ? (inboundMessages ?? []).filter((message) => message.draft_id === selectedDraft.id)
    : [];
  const selectedThreads = selectedDraft
    ? (inboundThreads ?? []).filter((thread) => thread.draft_id === selectedDraft.id)
    : [];

  async function handleReview(draftId: string, approved: boolean) {
    setIsReviewingDraftId(draftId);
    try {
      await sileo.promise(
        (async () => {
          const updated = await reviewDraft(draftId, approved);
          await mutateDrafts(
            (current) => current?.map((draft) => (draft.id === draftId ? { ...draft, ...updated } : draft)),
            false
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
          await mutateDrafts(
            (current) => current?.map((draft) => (draft.id === draftId ? { ...draft, status: "sent" as DraftStatus } : draft)),
            false
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
            <PageHeader title="Outreach" description="Gestion de borradores y actividad comercial" />
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
            description="Gestion de borradores y actividad comercial"
          />

          <div className="grid gap-6 lg:grid-cols-3">
            <DraftList
              drafts={drafts ?? []}
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

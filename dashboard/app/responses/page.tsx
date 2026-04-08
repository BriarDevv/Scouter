"use client";

import { useMemo, useState } from "react";
import {
  Inbox,
  LifeBuoy,
  MessagesSquare,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { sileo } from "sileo";
import { Button } from "@/components/ui/button";
import {
  classifyInboundMessage,
  classifyPendingInboundMessages,
  syncInboundMail,
} from "@/lib/api/client";
import { useApi } from "@/lib/hooks/use-swr-fetch";
import { POSITIVE_REPLY_LABELS } from "@/lib/constants";
import type {
  EmailThreadSummary,
  InboundMailStatus,
  InboundMessage,
  Lead,
  OutreachDraft,
  PaginatedResponse,
} from "@/types";

import { MessageList } from "@/components/responses/message-list";
import { ThreadDetail } from "@/components/responses/thread-detail";
import { LeadsPagination } from "@/components/responses/compose-area";

const LEADS_PAGE_SIZE = 50;

export default function ResponsesPage() {
  const [leadsPage, setLeadsPage] = useState(1);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isClassifying, setIsClassifying] = useState(false);
  const [classifyingMessageId, setClassifyingMessageId] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "pending" | "classified" | "failed">("all");

  const { data: messages, isLoading: messagesLoading, mutate: mutateMessages } = useApi<InboundMessage[]>("/mail/inbound/messages?limit=100");
  const { data: threads, mutate: mutateThreads } = useApi<EmailThreadSummary[]>("/mail/inbound/threads?limit=50");
  const { data: status, mutate: mutateStatus } = useApi<InboundMailStatus>("/mail/inbound/status");
  const { data: leadsResponse, mutate: mutateLeads } = useApi<PaginatedResponse<Lead>>(
    `/leads?page=${leadsPage}&page_size=${LEADS_PAGE_SIZE}`
  );
  const { data: drafts, mutate: mutateDrafts } = useApi<OutreachDraft[]>("/outreach/drafts");

  const loading = messagesLoading;
  const leads = leadsResponse?.items ?? [];
  const leadsTotal = leadsResponse?.total ?? 0;
  const leadsTotalPages = Math.max(1, Math.ceil(leadsTotal / LEADS_PAGE_SIZE));

  async function reloadAll() {
    await Promise.all([mutateMessages(), mutateThreads(), mutateStatus(), mutateLeads(), mutateDrafts()]);
  }

  const leadById = useMemo(
    () => new Map(leads.map((lead) => [lead.id, lead])),
    [leads]
  );
  const draftById = useMemo(
    () => new Map((drafts ?? []).map((draft) => [draft.id, draft])),
    [drafts]
  );
  const threadById = useMemo(
    () => new Map((threads ?? []).map((thread) => [thread.id, thread])),
    [threads]
  );

  const messagesList = messages ?? [];

  const filteredMessages = useMemo(() => {
    if (filter === "all") return messagesList;
    return messagesList.filter((message) => message.classification_status === filter);
  }, [filter, messagesList]);

  const recentRepliesCount = messagesList.length;
  const repliedLeadsCount = new Set(messagesList.map((m) => m.lead_id).filter(Boolean)).size;
  const positiveRepliesCount = messagesList.filter(
    (m) => m.classification_label && POSITIVE_REPLY_LABELS.includes(m.classification_label)
  ).length;
  const quoteRepliesCount = messagesList.filter(
    (m) => m.classification_label === "asked_for_quote"
  ).length;
  const meetingRepliesCount = messagesList.filter(
    (m) => m.classification_label === "asked_for_meeting"
  ).length;
  const pendingCount = messagesList.filter((m) => m.classification_status === "pending").length;
  const escalatedCount = messagesList.filter((m) => m.should_escalate_reviewer).length;

  async function handleSync() {
    setIsSyncing(true);
    try {
      await sileo.promise(syncInboundMail(), {
        loading: { title: "Sincronizando inbox..." },
        success: { title: "Inbox sincronizado" },
        error: (err: unknown) => ({
          title: "Error de sincronizacion",
          description: err instanceof Error ? err.message : "No se pudo sincronizar el inbox.",
        }),
      });
      await reloadAll();
    } finally {
      setIsSyncing(false);
    }
  }

  async function handleClassifyPending() {
    setIsClassifying(true);
    try {
      await sileo.promise(classifyPendingInboundMessages(25), {
        loading: { title: "Clasificando pendientes..." },
        success: { title: "Clasificacion completada" },
        error: (err: unknown) => ({
          title: "Error de clasificacion",
          description: err instanceof Error ? err.message : "No se pudieron clasificar los replies.",
        }),
      });
      await reloadAll();
    } finally {
      setIsClassifying(false);
    }
  }

  async function handleClassifyMessage(messageId: string) {
    setClassifyingMessageId(messageId);
    try {
      await sileo.promise(classifyInboundMessage(messageId), {
        loading: { title: "Clasificando reply..." },
        success: { title: "Reply clasificado" },
        error: (err: unknown) => ({
          title: "Error de clasificacion",
          description: err instanceof Error ? err.message : "No se pudo clasificar el reply.",
        }),
      });
      await reloadAll();
    } finally {
      setClassifyingMessageId(null);
    }
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[1400px] px-8 py-8">
        <div className="space-y-6">
          <PageHeader
            title="Respuestas"
            description="Inbox comercial grounded sobre inbound mail real, matching a deliveries y clasificacion con executor."
          >
            <Button
              variant="outline"
              className="rounded-xl gap-1.5"
              onClick={() => void handleSync()}
              disabled={isSyncing}
            >
              <RefreshCw className="h-4 w-4" />
              {isSyncing ? "Sincronizando..." : "Sync inbox"}
            </Button>
            <Button
              variant="outline"
              className="rounded-xl gap-1.5"
              onClick={() => void handleClassifyPending()}
              disabled={isClassifying || pendingCount === 0}
            >
              <Sparkles className="h-4 w-4" />
              {isClassifying ? "Clasificando..." : "Clasificar pendientes"}
            </Button>
          </PageHeader>

          <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
            <StatCard label="Replies recientes" value={recentRepliesCount} icon={Inbox} colorScheme="muted" />
            <StatCard label="Leads que respondieron" value={repliedLeadsCount} icon={MessagesSquare} colorScheme="emerald" />
            <StatCard
              label="Replies positivas"
              value={positiveRepliesCount}
              icon={Sparkles}
              colorScheme="cyan"
              subtitle={`${quoteRepliesCount} cotizacion · ${meetingRepliesCount} reunion`}
            />
            <StatCard label="Sugeridas a reviewer" value={escalatedCount} icon={LifeBuoy} colorScheme="fuchsia" />
          </div>

          <div className="grid gap-6 xl:grid-cols-[1.5fr,0.9fr]">
            <MessageList
              messages={filteredMessages}
              loading={loading}
              filter={filter}
              onFilterChange={setFilter}
              leadById={leadById}
              draftById={draftById}
              threadById={threadById}
              classifyingMessageId={classifyingMessageId}
              onClassifyMessage={(id) => void handleClassifyMessage(id)}
              onRefresh={() => void reloadAll()}
            />

            <div className="space-y-6">
              <ThreadDetail
                threads={threads ?? []}
                status={status ?? null}
                leadById={leadById}
              />

              <LeadsPagination
                leadsPage={leadsPage}
                leadsTotalPages={leadsTotalPages}
                leadsTotal={leadsTotal}
                onPageChange={setLeadsPage}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

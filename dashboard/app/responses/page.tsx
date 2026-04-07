"use client";

import { useEffect, useMemo, useState } from "react";
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
  getDrafts,
  getInboundMailStatus,
  getInboundMessages,
  getInboundThreads,
  getLeads,
  classifyInboundMessage,
  classifyPendingInboundMessages,
  syncInboundMail,
} from "@/lib/api/client";
import { POSITIVE_REPLY_LABELS } from "@/lib/constants";
import type {
  EmailThreadSummary,
  InboundMailStatus,
  InboundMessage,
  Lead,
  OutreachDraft,
} from "@/types";

import { MessageList } from "@/components/responses/message-list";
import { ThreadDetail } from "@/components/responses/thread-detail";
import { LeadsPagination } from "@/components/responses/compose-area";

const LEADS_PAGE_SIZE = 50;

export default function ResponsesPage() {
  const [messages, setMessages] = useState<InboundMessage[]>([]);
  const [threads, setThreads] = useState<EmailThreadSummary[]>([]);
  const [status, setStatus] = useState<InboundMailStatus | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [leadsPage, setLeadsPage] = useState(1);
  const [leadsTotal, setLeadsTotal] = useState(0);
  const [drafts, setDrafts] = useState<OutreachDraft[]>([]);
  const [loading, setLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isClassifying, setIsClassifying] = useState(false);
  const [classifyingMessageId, setClassifyingMessageId] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "pending" | "classified" | "failed">("all");

  const leadsTotalPages = Math.max(1, Math.ceil(leadsTotal / LEADS_PAGE_SIZE));

  async function loadInboxData() {
    setLoading(true);
    try {
      const [nextMessages, nextThreads, nextStatus, nextLeads, nextDrafts] = await Promise.all([
        getInboundMessages({ limit: 100 }),
        getInboundThreads({ limit: 50 }),
        getInboundMailStatus(),
        getLeads({ page: leadsPage, page_size: LEADS_PAGE_SIZE }),
        getDrafts(),
      ]);
      setMessages(nextMessages);
      setThreads(nextThreads);
      setStatus(nextStatus);
      setLeads(nextLeads.items);
      setLeadsTotal(nextLeads.total);
      setDrafts(nextDrafts);
    } catch (err) {
      sileo.error({
        title: "Error de carga",
        description: err instanceof Error ? err.message : "No se pudo cargar el inbox.",
      });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadInboxData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [leadsPage]);

  const leadById = useMemo(
    () => new Map(leads.map((lead) => [lead.id, lead])),
    [leads]
  );
  const draftById = useMemo(
    () => new Map(drafts.map((draft) => [draft.id, draft])),
    [drafts]
  );
  const threadById = useMemo(
    () => new Map(threads.map((thread) => [thread.id, thread])),
    [threads]
  );

  const filteredMessages = useMemo(() => {
    if (filter === "all") return messages;
    return messages.filter((message) => message.classification_status === filter);
  }, [filter, messages]);

  const recentRepliesCount = messages.length;
  const repliedLeadsCount = new Set(messages.map((m) => m.lead_id).filter(Boolean)).size;
  const positiveRepliesCount = messages.filter(
    (m) => m.classification_label && POSITIVE_REPLY_LABELS.includes(m.classification_label)
  ).length;
  const quoteRepliesCount = messages.filter(
    (m) => m.classification_label === "asked_for_quote"
  ).length;
  const meetingRepliesCount = messages.filter(
    (m) => m.classification_label === "asked_for_meeting"
  ).length;
  const pendingCount = messages.filter((m) => m.classification_status === "pending").length;
  const escalatedCount = messages.filter((m) => m.should_escalate_reviewer).length;

  async function handleSync() {
    setIsSyncing(true);
    try {
      await sileo.promise(syncInboundMail(), {
        loading: { title: "Sincronizando inbox…" },
        success: { title: "Inbox sincronizado" },
        error: (err: unknown) => ({
          title: "Error de sincronización",
          description: err instanceof Error ? err.message : "No se pudo sincronizar el inbox.",
        }),
      });
      await loadInboxData();
    } finally {
      setIsSyncing(false);
    }
  }

  async function handleClassifyPending() {
    setIsClassifying(true);
    try {
      await sileo.promise(classifyPendingInboundMessages(25), {
        loading: { title: "Clasificando pendientes…" },
        success: { title: "Clasificación completada" },
        error: (err: unknown) => ({
          title: "Error de clasificación",
          description: err instanceof Error ? err.message : "No se pudieron clasificar los replies.",
        }),
      });
      await loadInboxData();
    } finally {
      setIsClassifying(false);
    }
  }

  async function handleClassifyMessage(messageId: string) {
    setClassifyingMessageId(messageId);
    try {
      await sileo.promise(classifyInboundMessage(messageId), {
        loading: { title: "Clasificando reply…" },
        success: { title: "Reply clasificado" },
        error: (err: unknown) => ({
          title: "Error de clasificación",
          description: err instanceof Error ? err.message : "No se pudo clasificar el reply.",
        }),
      });
      await loadInboxData();
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
            description="Inbox comercial grounded sobre inbound mail real, matching a deliveries y clasificación con executor."
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
            <StatCard label="Replies recientes" value={recentRepliesCount} icon={Inbox} colorScheme="violet" />
            <StatCard label="Leads que respondieron" value={repliedLeadsCount} icon={MessagesSquare} colorScheme="emerald" />
            <StatCard
              label="Replies positivas"
              value={positiveRepliesCount}
              icon={Sparkles}
              colorScheme="cyan"
              subtitle={`${quoteRepliesCount} cotización · ${meetingRepliesCount} reunión`}
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
              onRefresh={() => void loadInboxData()}
            />

            <div className="space-y-6">
              <ThreadDetail
                threads={threads}
                status={status}
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

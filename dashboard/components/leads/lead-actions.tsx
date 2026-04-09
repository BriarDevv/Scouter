"use client";

import { useState } from "react";
import {
  generateDraft,
  generateBrief,
  getTaskStatus,
  reviewDraft,
  reviewLeadWithIA,
  runFullPipeline,
  runResearch,
  sendOutreachDraft,
  updateLeadStatus,
} from "@/lib/api/client";
import type { CommercialBrief, LeadResearchReport, TaskStatusRecord } from "@/types";
import { sileo } from "sileo";

export interface LeadActionsState {
  isRunningPipeline: boolean;
  isGeneratingDraft: boolean;
  isApprovingLead: boolean;
  isReviewingDraftId: string | null;
  isSendingDraftId: string | null;
  isReviewingLead: boolean;
  isRunningResearch: boolean;
  isGeneratingBrief: boolean;
}

export interface LeadActionsHandlers {
  handleRunPipeline: () => void;
  handleGenerateDraft: () => void;
  handleApproveLead: () => void;
  handleReviewDraft: (draftId: string, approved: boolean) => void;
  handleSendDraft: (draftId: string) => void;
  handleGenerateWhatsAppDraft: () => void;
  handleReviewLead: () => void;
  handleRunResearch: () => void;
  handleGenerateBrief: () => void;
}

interface UseLeadActionsOptions {
  leadId: string | null;
  onRefresh: () => Promise<void>;
  onLatestTask: (task: TaskStatusRecord) => void;
  onResearch: (report: LeadResearchReport) => void;
  onBrief: (brief: CommercialBrief) => void;
}

export function useLeadActions({
  leadId,
  onRefresh,
  onLatestTask,
  onResearch,
  onBrief,
}: UseLeadActionsOptions): LeadActionsState & LeadActionsHandlers {
  const [isRunningPipeline, setIsRunningPipeline] = useState(false);
  const [isGeneratingDraft, setIsGeneratingDraft] = useState(false);
  const [isApprovingLead, setIsApprovingLead] = useState(false);
  const [isReviewingDraftId, setIsReviewingDraftId] = useState<string | null>(null);
  const [isSendingDraftId, setIsSendingDraftId] = useState<string | null>(null);
  const [isReviewingLead, setIsReviewingLead] = useState(false);
  const [isRunningResearch, setIsRunningResearch] = useState(false);
  const [isGeneratingBrief, setIsGeneratingBrief] = useState(false);

  async function handleRunPipeline() {
    if (!leadId) return;
    setIsRunningPipeline(true);
    try {
      await sileo.promise(
        (async () => {
          const task = await runFullPipeline(leadId);
          const taskStatus = await getTaskStatus(task.task_id);
          onLatestTask(taskStatus);
          await onRefresh();
        })(),
        {
          loading: { title: "Ejecutando pipeline..." },
          success: { title: "Pipeline completado" },
          error: (err: unknown) => ({
            title: "Error en pipeline",
            description: err instanceof Error ? err.message : "No se pudo ejecutar.",
          }),
        }
      );
    } finally {
      setIsRunningPipeline(false);
    }
  }

  async function handleGenerateDraft() {
    if (!leadId) return;
    setIsGeneratingDraft(true);
    try {
      await sileo.promise(
        (async () => {
          await generateDraft(leadId);
          await onRefresh();
        })(),
        {
          loading: { title: "Generando borrador..." },
          success: { title: "Borrador generado" },
          error: (err: unknown) => ({
            title: "Error al generar borrador",
            description: err instanceof Error ? err.message : "No se pudo generar.",
          }),
        }
      );
    } finally {
      setIsGeneratingDraft(false);
    }
  }

  async function handleGenerateWhatsAppDraft() {
    if (!leadId) return;
    setIsGeneratingDraft(true);
    try {
      await sileo.promise(
        (async () => {
          await generateDraft(leadId, "whatsapp");
          await onRefresh();
        })(),
        {
          loading: { title: "Generando borrador WhatsApp..." },
          success: { title: "Borrador WhatsApp generado" },
          error: (err: unknown) => ({
            title: "Error al generar borrador",
            description: err instanceof Error ? err.message : "No se pudo generar.",
          }),
        }
      );
    } finally {
      setIsGeneratingDraft(false);
    }
  }

  async function handleApproveLead() {
    if (!leadId) return;
    setIsApprovingLead(true);
    try {
      await sileo.promise(
        (async () => {
          await updateLeadStatus(leadId, "approved");
          await onRefresh();
        })(),
        {
          loading: { title: "Aprobando lead..." },
          success: { title: "Lead aprobado" },
          error: (err: unknown) => ({
            title: "Error al aprobar",
            description: err instanceof Error ? err.message : "No se pudo aprobar.",
          }),
        }
      );
    } finally {
      setIsApprovingLead(false);
    }
  }

  async function handleReviewDraft(draftId: string, approved: boolean) {
    setIsReviewingDraftId(draftId);
    try {
      await sileo.promise(
        (async () => {
          await reviewDraft(draftId, approved);
          await onRefresh();
        })(),
        {
          loading: { title: approved ? "Aprobando draft..." : "Rechazando draft..." },
          success: { title: approved ? "Draft aprobado" : "Draft rechazado" },
          error: (err: unknown) => ({
            title: "Error al revisar draft",
            description: err instanceof Error ? err.message : "No se pudo revisar.",
          }),
        }
      );
    } finally {
      setIsReviewingDraftId(null);
    }
  }

  async function handleSendDraft(draftId: string) {
    setIsSendingDraftId(draftId);
    try {
      await sileo.promise(
        (async () => {
          await sendOutreachDraft(draftId);
          await onRefresh();
        })(),
        {
          loading: { title: "Enviando draft..." },
          success: { title: "Draft enviado" },
          error: (err: unknown) => ({
            title: "Error al enviar",
            description: err instanceof Error ? err.message : "No se pudo enviar.",
          }),
        }
      );
    } finally {
      setIsSendingDraftId(null);
    }
  }

  async function handleRunResearch() {
    if (!leadId) return;
    setIsRunningResearch(true);
    try {
      await sileo.promise(
        (async () => {
          const res = await runResearch(leadId);
          onResearch(res);
        })(),
        {
          loading: { title: "Investigando lead..." },
          success: { title: "Investigacion completada" },
          error: (err: unknown) => ({
            title: "Error en investigacion",
            description: err instanceof Error ? err.message : "No se pudo investigar.",
          }),
        }
      );
    } finally {
      setIsRunningResearch(false);
    }
  }

  async function handleGenerateBrief() {
    if (!leadId) return;
    setIsGeneratingBrief(true);
    try {
      await sileo.promise(
        (async () => {
          const res = await generateBrief(leadId);
          onBrief(res);
        })(),
        {
          loading: { title: "Generando brief comercial..." },
          success: { title: "Brief generado" },
          error: (err: unknown) => ({
            title: "Error al generar brief",
            description: err instanceof Error ? err.message : "No se pudo generar.",
          }),
        }
      );
    } finally {
      setIsGeneratingBrief(false);
    }
  }

  async function handleReviewLead() {
    if (!leadId) return;
    setIsReviewingLead(true);
    try {
      await sileo.promise(
        (async () => {
          await reviewLeadWithIA(leadId);
          await onRefresh();
        })(),
        {
          loading: { title: "Reviewer IA analizando..." },
          success: { title: "Análisis del Reviewer completado" },
          error: (err: unknown) => ({
            title: "Error en Reviewer IA",
            description: err instanceof Error ? err.message : "No se pudo analizar.",
          }),
        }
      );
    } finally {
      setIsReviewingLead(false);
    }
  }

  return {
    isRunningPipeline,
    isGeneratingDraft,
    isApprovingLead,
    isReviewingDraftId,
    isSendingDraftId,
    isReviewingLead,
    isRunningResearch,
    isGeneratingBrief,
    handleRunPipeline: () => void handleRunPipeline(),
    handleGenerateDraft: () => void handleGenerateDraft(),
    handleGenerateWhatsAppDraft: () => void handleGenerateWhatsAppDraft(),
    handleApproveLead: () => void handleApproveLead(),
    handleReviewDraft: (draftId: string, approved: boolean) => void handleReviewDraft(draftId, approved),
    handleSendDraft: (draftId: string) => void handleSendDraft(draftId),
    handleReviewLead: () => void handleReviewLead(),
    handleRunResearch: () => void handleRunResearch(),
    handleGenerateBrief: () => void handleGenerateBrief(),
  };
}

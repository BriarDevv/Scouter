import { useCallback, useEffect, useState } from "react";
import { sileo } from "sileo";
import { apiFetch } from "@/lib/api/client";
import { useVisibleInterval } from "@/lib/hooks/use-visible-interval";
import type { PipelineStatus } from "@/components/dashboard/pipeline-controls";

interface PipelineBatchStatus {
  status: string;
  ok?: boolean;
  message?: string;
  task_id?: string;
  processed?: number;
  total?: number;
  current_lead?: string | null;
  current_step?: string;
  error?: string;
  crawl_rounds?: number;
  leads_from_crawl?: number;
}

export function usePipeline(onComplete: () => void) {
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus>("idle");
  const [pipelineProgress, setPipelineProgress] = useState<string | null>(null);

  // ── Check on mount ──
  useEffect(() => {
    let active = true;
    async function checkPipeline() {
      try {
        const data = await apiFetch<PipelineBatchStatus>("/pipelines/batch/status");
        if (!active) return;
        if (data.status === "running" || data.status === "stopping") {
          setPipelineStatus(data.status === "stopping" ? "stopping" : "running");
          setPipelineProgress(data.current_lead
            ? `${data.current_lead} (${data.processed ?? 0}/${data.total ?? 0}) — ${data.current_step ?? ""}`
            : "Iniciando...");
        }
      } catch {}
    }
    checkPipeline();
    return () => { active = false; };
  }, []);

  // ── Poll ──
  const pollPipeline = useCallback(async () => {
    if (pipelineStatus !== "running") return;
    try {
      const data = await apiFetch<PipelineBatchStatus>("/pipelines/batch/status");
      if (data.status === "done") {
        setPipelineStatus("done");
        const crawlNote = data.crawl_rounds ? ` (${data.crawl_rounds} crawls, ${data.leads_from_crawl ?? 0} encontrados)` : "";
        setPipelineProgress(`${data.processed ?? 0} leads procesados${crawlNote}`);
        sileo.success({ title: `Pipeline completado: ${data.processed ?? 0} leads` });
        onComplete();
      } else if (data.status === "error") {
        setPipelineStatus("error");
        setPipelineProgress(data.error ?? "Error");
        sileo.error({ title: data.error ?? "Error en pipeline" });
      } else if (data.status === "stopped") {
        setPipelineStatus("idle");
        setPipelineProgress(null);
        sileo.success({ title: "Pipeline detenido" });
      } else if (data.status === "running") {
        const step = data.current_step ?? "";
        const crawlInfo = data.crawl_rounds ? ` | crawl #${data.crawl_rounds}` : "";
        if (step === "crawling") {
          setPipelineProgress(`Buscando leads — ${data.current_lead ?? "crawling..."}${crawlInfo}`);
        } else if (data.current_lead) {
          setPipelineProgress(`${data.current_lead} (${data.processed ?? 0}/${data.total ?? 0}) — ${step}${crawlInfo}`);
        } else {
          setPipelineProgress("Iniciando...");
        }
      }
    } catch {}
  }, [pipelineStatus, onComplete]);

  useVisibleInterval(pollPipeline, 2000);

  // ── Actions ──
  const handleStart = useCallback(async () => {
    try {
      const data = await apiFetch<PipelineBatchStatus>("/pipelines/batch", { method: "POST" });
      if (data.ok) {
        setPipelineStatus("running");
        setPipelineProgress("Iniciando...");
        sileo.success({ title: "Pipeline iniciado", description: data.message });
      } else {
        sileo.error({ title: data.message ?? "Error al iniciar pipeline" });
      }
    } catch {
      sileo.error({ title: "Error de conexion al iniciar pipeline" });
    }
  }, []);

  const handleStop = useCallback(async () => {
    try {
      await apiFetch("/pipelines/batch/stop", { method: "POST" });
      setPipelineStatus("stopping");
      setPipelineProgress("Deteniendo...");
    } catch {
      sileo.error({ title: "Error al detener pipeline" });
    }
  }, []);

  return { pipelineStatus, pipelineProgress, handleStart, handleStop };
}

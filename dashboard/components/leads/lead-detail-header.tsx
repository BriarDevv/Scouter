"use client";

import { Button } from "@/components/ui/button";
import {
  QualityBadge,
  StatusBadge,
} from "@/components/shared/status-badge";
import { RelativeTime } from "@/components/shared/relative-time";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import type { Lead } from "@/types";
import Link from "next/link";
import {
  ArrowLeft, RefreshCw, Mail, MessageCircle, CheckCircle, ShieldCheck, Loader2,
} from "lucide-react";

interface LeadDetailHeaderProps {
  lead: Lead;
  isRunningPipeline: boolean;
  isReviewingLead: boolean;
  isGeneratingDraft: boolean;
  isApprovingLead: boolean;
  onRunPipeline: () => void;
  onReviewLead: () => void;
  onGenerateDraft: () => void;
  onGenerateWhatsAppDraft: () => void;
  onApproveLead: () => void;
}

export function LeadDetailHeader({
  lead,
  isRunningPipeline,
  isReviewingLead,
  isGeneratingDraft,
  isApprovingLead,
  onRunPipeline,
  onReviewLead,
  onGenerateDraft,
  onGenerateWhatsAppDraft,
  onApproveLead,
}: LeadDetailHeaderProps) {
  return (
    <div className="flex items-start justify-between">
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <Link href="/leads" className="flex items-center justify-center h-7 w-7 rounded-lg hover:bg-muted transition-colors shrink-0">
            <ArrowLeft className="h-4 w-4 text-muted-foreground" />
          </Link>
          <h1 className="text-2xl font-semibold text-foreground font-heading">{lead.business_name}</h1>
          <StatusBadge status={lead.status} />
          <QualityBadge quality={lead.quality} />
        </div>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          {lead.industry && <span>{lead.industry}</span>}
          {lead.city && <span>{lead.city}{lead.zone ? `, ${lead.zone}` : ""}</span>}
          <span>
            Creado <RelativeTime date={lead.created_at} />
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Tooltip>
          <TooltipTrigger
            render={
              <Button
                variant="outline"
                size="sm"
                className="rounded-xl gap-1.5"
                onClick={onRunPipeline}
                disabled={isRunningPipeline}
              />
            }
          >
            {isRunningPipeline ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            Pipeline
          </TooltipTrigger>
          <TooltipContent>Ejecutar enrichment, scoring y análisis IA</TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger
            render={
              <Button
                variant="outline"
                size="sm"
                className="rounded-xl gap-1.5 text-amber-700 border-amber-200 hover:bg-amber-50 dark:hover:bg-amber-950/20"
                onClick={onReviewLead}
                disabled={isReviewingLead}
              />
            }
          >
            {isReviewingLead ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ShieldCheck className="h-3.5 w-3.5" />}
            Reviewer
          </TooltipTrigger>
          <TooltipContent>Analizar con Reviewer IA (27B)</TooltipContent>
        </Tooltip>

        {lead.email && (
          <Tooltip>
            <TooltipTrigger
              render={
                <Button
                  variant="outline"
                  size="sm"
                  className="rounded-xl gap-1.5"
                  onClick={onGenerateDraft}
                  disabled={isGeneratingDraft}
                />
              }
            >
              {isGeneratingDraft ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Mail className="h-3.5 w-3.5" />}
              Draft Email
            </TooltipTrigger>
            <TooltipContent>Generar borrador de email con IA</TooltipContent>
          </Tooltip>
        )}

        {lead.phone && (
          <Tooltip>
            <TooltipTrigger
              render={
                <Button
                  variant="outline"
                  size="sm"
                  className="rounded-xl gap-1.5"
                  onClick={onGenerateWhatsAppDraft}
                  disabled={isGeneratingDraft}
                />
              }
            >
              {isGeneratingDraft ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <MessageCircle className="h-3.5 w-3.5" />}
              Draft WhatsApp
            </TooltipTrigger>
            <TooltipContent>Generar borrador de WhatsApp con IA</TooltipContent>
          </Tooltip>
        )}

        <Tooltip>
          <TooltipTrigger
            render={
              <Button
                variant="outline"
                size="sm"
                className="rounded-xl gap-1.5 text-emerald-700 border-emerald-200 hover:bg-emerald-50 dark:hover:bg-emerald-950/20"
                onClick={onApproveLead}
                disabled={isApprovingLead}
              />
            }
          >
            {isApprovingLead ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle className="h-3.5 w-3.5" />}
            Aprobar
          </TooltipTrigger>
          <TooltipContent>Aprobar lead para outreach</TooltipContent>
        </Tooltip>
      </div>
    </div>
  );
}

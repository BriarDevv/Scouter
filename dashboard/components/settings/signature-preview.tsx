"use client";

import { CalendarDays, ExternalLink, Globe } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SignaturePreviewProps {
  brandName: string;
  signerName: string;
  signerRole: string;
  signerCompany: string;
  portfolioUrl: string;
  websiteUrl: string;
  calendarUrl: string;
  cta: string;
  closingLine: string;
  includePortfolio: boolean;
}

function BrandAvatar({ name }: { name: string }) {
  const initials =
    name
      .split(/\s+/)
      .slice(0, 2)
      .map((w) => w[0]?.toUpperCase() ?? "")
      .join("") || "?";

  return (
    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-border bg-card text-sm font-semibold text-foreground font-heading select-none">
      {initials}
    </div>
  );
}

export function SignaturePreview({
  brandName,
  signerName,
  signerRole,
  signerCompany,
  portfolioUrl,
  websiteUrl,
  calendarUrl,
  cta,
  closingLine,
  includePortfolio,
}: SignaturePreviewProps) {
  const hasName = signerName.trim().length > 0;
  const hasRole = signerRole.trim().length > 0;
  const hasCompany = signerCompany.trim().length > 0;
  const hasCta = cta.trim().length > 0;
  const hasClosing = closingLine.trim().length > 0;
  const hasWeb = websiteUrl.trim().length > 0;
  const hasCal = calendarUrl.trim().length > 0;
  const hasPort = includePortfolio && portfolioUrl.trim().length > 0;
  const hasAnyLink = hasWeb || hasCal || hasPort;

  const displayName = hasName ? signerName : "Tu nombre";
  const displayRole = hasRole ? signerRole : "Tu cargo";
  const displayCompany = hasCompany
    ? signerCompany
    : brandName.trim() || "Tu empresa";

  return (
    <div className="space-y-4">
      <div className="min-w-0 space-y-3">
          <div className="flex items-start gap-3">
            <BrandAvatar name={brandName || displayName} />
            <div className="min-w-0 flex-1">
              <p className="truncate font-heading text-sm font-semibold leading-tight text-foreground">
                {displayName}
              </p>
              <p className="mt-0.5 truncate text-xs text-muted-foreground">
                {[displayRole, displayCompany].filter(Boolean).join(" · ")}
              </p>
            </div>
          </div>

          {hasClosing && (
            <p className="border-t border-border/60 pt-3 text-xs leading-relaxed text-foreground/80">
              {closingLine}
            </p>
          )}

          {hasCta && (
            <p className="text-xs font-medium text-foreground">{cta}</p>
          )}
        </div>

      {hasAnyLink && (
          <div className="flex flex-col gap-1.5 border-t border-border/60 pt-3">
            {hasWeb && (
              <div className="flex min-w-0 items-center gap-1.5">
                <Globe className="h-3 w-3 shrink-0 text-muted-foreground/60" />
                <span className="truncate font-data text-[11px] text-muted-foreground">
                  {websiteUrl}
                </span>
              </div>
            )}
            {hasCal && (
              <div className="flex min-w-0 items-center gap-1.5">
                <CalendarDays className="h-3 w-3 shrink-0 text-muted-foreground/60" />
                <span className="truncate font-data text-[11px] text-muted-foreground">
                  {calendarUrl}
                </span>
              </div>
            )}
            {hasPort && (
              <div className="flex min-w-0 items-center gap-1.5">
                <ExternalLink className="h-3 w-3 shrink-0 text-muted-foreground/60" />
                <span className="truncate font-data text-[11px] text-muted-foreground">
                  {portfolioUrl}
                </span>
              </div>
            )}
        </div>
      )}
    </div>
  );
}

"use client";

import { ExternalLink, Globe } from "lucide-react";

interface SignaturePreviewProps {
  form: {
    signature_name: string;
    signature_role: string;
    signature_company: string;
    portfolio_url: string;
    website_url: string;
    calendar_url: string;
    signature_cta: string;
    default_closing_line: string;
    signature_include_portfolio: boolean;
  };
}

export function SignaturePreview({ form }: SignaturePreviewProps) {
  const hasContent = form.signature_name || form.signature_role || form.signature_company;
  if (!hasContent) {
    return (
      <div className="flex items-center justify-center rounded-2xl border border-dashed border-border bg-muted p-8">
        <p className="text-sm text-muted-foreground">
          Completá los datos para ver la preview
        </p>
      </div>
    );
  }
  return (
    <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
      <p className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Preview de firma
      </p>
      <div className="border-t border-border pt-4 font-mono text-sm text-foreground/80">
        {form.default_closing_line && (
          <p className="mb-3 text-muted-foreground">{form.default_closing_line}</p>
        )}
        {form.signature_name && (
          <p className="font-semibold text-foreground">{form.signature_name}</p>
        )}
        {form.signature_role && <p className="text-muted-foreground">{form.signature_role}</p>}
        {form.signature_company && <p className="text-muted-foreground">{form.signature_company}</p>}
        {(form.website_url || form.portfolio_url) && (
          <div className="mt-2 flex flex-col gap-0.5 text-xs text-muted-foreground">
            {form.website_url && (
              <span className="flex items-center gap-1">
                <Globe className="h-3 w-3" />
                {form.website_url}
              </span>
            )}
            {form.signature_include_portfolio && form.portfolio_url && (
              <span className="flex items-center gap-1">
                <ExternalLink className="h-3 w-3" />
                Portfolio: {form.portfolio_url}
              </span>
            )}
            {form.calendar_url && (
              <span className="flex items-center gap-1 text-muted-foreground">
                {form.calendar_url}
              </span>
            )}
          </div>
        )}
        {form.signature_cta && (
          <p className="mt-3 italic text-muted-foreground">{form.signature_cta}</p>
        )}
      </div>
    </div>
  );
}

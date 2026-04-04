"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { getSetupReadiness } from "@/lib/api/client";
import type { SetupReadiness } from "@/types";

const ALLOWED_WHILE_LOCKED = new Set(["/onboarding", "/settings"]);

export function ReadinessGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [readiness, setReadiness] = useState<SetupReadiness | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const hasChecked = useRef(false);

  useEffect(() => {
    // Once the dashboard is confirmed unlocked, skip subsequent checks
    if (hasChecked.current && readiness?.dashboard_unlocked) return;

    let cancelled = false;

    async function load() {
      try {
        const data = await getSetupReadiness();
        if (!cancelled) {
          hasChecked.current = true;
          setReadiness(data);
          setFailed(false);
        }
      } catch {
        if (!cancelled) setFailed(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  const isAllowedWhileLocked = useMemo(() => ALLOWED_WHILE_LOCKED.has(pathname), [pathname]);

  useEffect(() => {
    if (loading || failed || !readiness) return;
    if (!readiness.dashboard_unlocked && !isAllowedWhileLocked) {
      router.replace(`/onboarding?next=${encodeURIComponent(pathname)}`);
    }
  }, [failed, isAllowedWhileLocked, loading, pathname, readiness, router]);

  if (loading && !isAllowedWhileLocked) {
    return (
      <div className="flex flex-1 items-center justify-center p-8 text-sm text-muted-foreground">
        Validando estado inicial de Scouter…
      </div>
    );
  }

  if (!failed && readiness && !readiness.dashboard_unlocked && !isAllowedWhileLocked) {
    return null;
  }

  return <>{children}</>;
}

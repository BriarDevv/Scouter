"use client";

import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { getSetupReadiness } from "@/lib/api/client";
import type { SetupReadiness } from "@/types";

const ALLOWED_WHILE_LOCKED = new Set(["/onboarding", "/settings"]);
const UNLOCKED_KEY = "scouter-dashboard-unlocked";

export function ReadinessGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [readiness, setReadiness] = useState<SetupReadiness | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const hasChecked = useRef(false);
  const [cachedUnlocked, setCachedUnlocked] = useState(false);

  // Read cached unlock state before paint to avoid blocking flash
  useLayoutEffect(() => {
    try {
      if (localStorage.getItem(UNLOCKED_KEY) === "true") setCachedUnlocked(true);
    } catch {}
  }, []);

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
          // Cache unlock state for instant next load
          try {
            if (data.dashboard_unlocked) {
              localStorage.setItem(UNLOCKED_KEY, "true");
            } else {
              localStorage.removeItem(UNLOCKED_KEY);
              setCachedUnlocked(false);
            }
          } catch {}
        }
      } catch (err) {
        console.error("readiness_fetch_failed", err);
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

  // If cached as unlocked, render immediately while API validates in background
  if (cachedUnlocked) {
    return <>{children}</>;
  }

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

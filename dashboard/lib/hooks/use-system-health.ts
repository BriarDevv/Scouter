"use client";

import { useCallback, useRef, useState } from "react";
import { getSystemHealth } from "@/lib/api/client";
import { useVisibleInterval } from "@/lib/hooks/use-visible-interval";
import type { HealthComponent, SystemHealth } from "@/types";

interface UseSystemHealthResult {
  health: SystemHealth | null;
  components: HealthComponent[];
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useSystemHealth(pollMs = 30_000): UseSystemHealthResult {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const isInitial = useRef(true);

  const fetchHealth = useCallback(async () => {
    if (isInitial.current) setLoading(true);
    try {
      const data = await getSystemHealth();
      setHealth(data);
      setError(null);
    } catch (err) {
      console.warn("Health check failed", err);
      setError("Sin conexión al backend");
    } finally {
      setLoading(false);
      isInitial.current = false;
    }
  }, []);

  useVisibleInterval(() => void fetchHealth(), pollMs);

  return {
    health,
    components: health?.components ?? [],
    loading,
    error,
    refresh: fetchHealth,
  };
}

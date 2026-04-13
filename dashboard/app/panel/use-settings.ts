import { useCallback, useEffect, useRef, useState } from "react";
import { sileo } from "sileo";
import {
  getOperationalSettings,
  updateOperationalSettings,
  setRuntimeMode,
} from "@/lib/api/client";
import { IA_FEATURES, CHANNEL_FEATURES } from "./feature-defs";
import type { OperationalSettings, RuntimeMode } from "@/types";

export function useSettings() {
  const [settings, setSettings] = useState<OperationalSettings | null>(null);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [runtimeMode, setRuntimeModeState] = useState<RuntimeMode>("safe");
  const [savingMode, setSavingMode] = useState(false);
  const isInitialSettings = useRef(true);
  const [loadingSettings, setLoadingSettings] = useState(true);

  const loadSettings = useCallback(async () => {
    if (isInitialSettings.current) setLoadingSettings(true);
    try {
      const data = await getOperationalSettings();
      setSettings(data);
      setRuntimeModeState((data.runtime_mode as RuntimeMode) ?? "safe");
    } catch (err) {
      console.error("settings_fetch_failed", err);
    } finally {
      setLoadingSettings(false);
      isInitialSettings.current = false;
    }
  }, []);

  useEffect(() => { loadSettings(); }, [loadSettings]);

  const handleSetRuntimeMode = useCallback(async (mode: RuntimeMode) => {
    setSavingMode(true);
    try {
      await setRuntimeMode(mode);
      setRuntimeModeState(mode);
      sileo.success({ title: `Modo: ${mode}` });
    } catch (err) {
      sileo.error({ title: "Error al cambiar modo", description: err instanceof Error ? err.message : "" });
    } finally {
      setSavingMode(false);
    }
  }, []);

  const toggleFeature = useCallback(async (key: keyof OperationalSettings, value: boolean) => {
    if (!settings) return;
    setSavingKey(key);
    try {
      const updated = await updateOperationalSettings({ [key]: value });
      setSettings(updated);
      sileo.success({ title: value ? "Activado" : "Desactivado", description: [...IA_FEATURES, ...CHANNEL_FEATURES].find((f) => f.key === key)?.label });
    } catch (err) {
      sileo.error({ title: "Error al cambiar configuracion", description: err instanceof Error ? err.message : "" });
    } finally {
      setSavingKey(null);
    }
  }, [settings]);

  return {
    settings,
    savingKey,
    runtimeMode,
    savingMode,
    loadingSettings,
    loadSettings,
    handleSetRuntimeMode,
    toggleFeature,
  };
}

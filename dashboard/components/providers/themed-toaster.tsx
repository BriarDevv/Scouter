"use client";

import { Toaster } from "sileo";
import { useTheme } from "./theme-provider";

export function ThemedToaster() {
  const { resolved } = useTheme();
  const isDark = resolved === "dark";

  return (
    <Toaster
      position="bottom-center"
      theme={isDark ? "dark" : "light"}
      options={{
        autopilot: true,
        fill: isDark ? "#2b2b2b" : "#ffffff",
        styles: {
          title: isDark ? "!text-white !text-center" : "!text-black !text-center",
          description: isDark ? "!text-white/60 !text-center" : "!text-black/50 !text-center",
        },
      }}
    />
  );
}

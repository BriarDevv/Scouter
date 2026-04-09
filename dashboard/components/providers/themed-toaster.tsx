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
          title: isDark ? "!text-white" : "!text-black",
          description: isDark ? "!text-white/60" : "!text-black/50",
        },
      }}
    />
  );
}

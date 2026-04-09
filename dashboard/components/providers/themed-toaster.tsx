"use client";

import { Toaster } from "sileo";
import { useTheme } from "./theme-provider";

export function ThemedToaster() {
  const { resolved } = useTheme();
  return (
    <Toaster
      position="bottom-center"
      theme={resolved === "dark" ? "dark" : "light"}
      options={{ autopilot: true }}
    />
  );
}

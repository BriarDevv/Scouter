"use client";

import dynamic from "next/dynamic";

const LayoutShell = dynamic(
  () => import("@/components/layout/layout-shell").then((m) => m.LayoutShell),
  { ssr: false }
);

export function LayoutShellClient({ children }: { children: React.ReactNode }) {
  return <LayoutShell>{children}</LayoutShell>;
}

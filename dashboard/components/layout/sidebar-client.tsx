"use client";

import dynamic from "next/dynamic";

const Sidebar = dynamic(
  () => import("@/components/layout/sidebar").then((m) => m.Sidebar),
  { ssr: false }
);

export function SidebarClient() {
  return <Sidebar />;
}

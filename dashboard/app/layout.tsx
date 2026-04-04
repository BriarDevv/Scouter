import type { Metadata } from "next";
import localFont from "next/font/local";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { Sidebar } from "@/components/layout/sidebar";
import { LayoutShell } from "@/components/layout/layout-shell";
import { ReadinessGate } from "@/components/layout/readiness-gate";
import { ChatPanelProvider } from "@/lib/hooks/use-chat-panel";
import { ThemedToaster } from "@/components/providers/themed-toaster";
import "./globals.css";

const satoshi = localFont({
  src: [{ path: "./fonts/Satoshi-Variable.woff2", style: "normal" }],
  variable: "--font-heading",
  display: "swap",
});

const geistSans = localFont({
  src: "./fonts/Geist-Variable.woff2",
  variable: "--font-geist-sans",
  display: "swap",
});

const geistMono = localFont({
  src: "./fonts/GeistMono-Variable.woff2",
  variable: "--font-geist-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Scouter — Lead Prospecting Dashboard",
  description: "Sistema privado de prospección comercial para desarrollo web",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{if(!localStorage.getItem("scouter-theme")&&localStorage.getItem("clawscout-theme")){localStorage.setItem("scouter-theme",localStorage.getItem("clawscout-theme"))}if(!localStorage.getItem("scouter-sidebar-collapsed")&&localStorage.getItem("clawscout-sidebar-collapsed")){localStorage.setItem("scouter-sidebar-collapsed",localStorage.getItem("clawscout-sidebar-collapsed"))}var t=localStorage.getItem("scouter-theme");if(t==="dark"||(t!=="light"&&matchMedia("(prefers-color-scheme:dark)").matches))document.documentElement.classList.add("dark");if(localStorage.getItem("scouter-sidebar-collapsed")==="true")document.documentElement.classList.add("sidebar-collapsed")}catch(e){}})()`,
          }}
        />
      </head>
      <body className={`${satoshi.variable} ${geistSans.variable} ${geistMono.variable} antialiased bg-sidebar`}>
        <ThemeProvider>
          <TooltipProvider>
            <ChatPanelProvider>
              <Sidebar />
              <LayoutShell>
                <ReadinessGate>{children}</ReadinessGate>
              </LayoutShell>
            </ChatPanelProvider>
            <ThemedToaster />
          </TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}

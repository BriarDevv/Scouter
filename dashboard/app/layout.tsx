import type { Metadata } from "next";
import localFont from "next/font/local";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { Sidebar } from "@/components/layout/sidebar";
import { LayoutShell } from "@/components/layout/layout-shell";
import { ChatPanel } from "@/components/chat/chat-panel";
import { ChatPanelProvider } from "@/lib/hooks/use-chat-panel";
import { ThemedToaster } from "@/components/providers/themed-toaster";
import "./globals.css";

const satoshi = localFont({
  src: [
    { path: "./fonts/Satoshi-Variable.woff2", style: "normal" },
    { path: "./fonts/Satoshi-VariableItalic.woff2", style: "italic" },
  ],
  variable: "--font-heading",
  display: "swap",
});

export const metadata: Metadata = {
  title: "ClawScout — Lead Prospecting Dashboard",
  description: "Sistema privado de prospección comercial para desarrollo web",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem("clawscout-theme");if(t==="dark"||(t!=="light"&&matchMedia("(prefers-color-scheme:dark)").matches))document.documentElement.classList.add("dark")}catch(e){}})()`,
          }}
        />
      </head>
      <body
        className={`${satoshi.variable} ${GeistSans.variable} ${GeistMono.variable} antialiased bg-sidebar`}
      >
        <ThemeProvider>
          <TooltipProvider>
            <ChatPanelProvider>
              <Sidebar />
              <LayoutShell>{children}</LayoutShell>
              <ChatPanel />
            </ChatPanelProvider>
            <ThemedToaster />
          </TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}

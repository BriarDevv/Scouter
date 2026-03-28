import type { Metadata } from "next";
import { Plus_Jakarta_Sans, Inter, Geist_Mono } from "next/font/google";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { Sidebar } from "@/components/layout/sidebar";
import { LayoutShell } from "@/components/layout/layout-shell";
import { ChatPanel } from "@/components/chat/chat-panel";
import { ChatPanelProvider } from "@/lib/hooks/use-chat-panel";
import { ThemedToaster } from "@/components/providers/themed-toaster";
import "./globals.css";

const plusJakarta = Plus_Jakarta_Sans({
  variable: "--font-heading",
  subsets: ["latin"],
  weight: ["500", "600", "700", "800"],
});

const inter = Inter({
  variable: "--font-body",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
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
        className={`${plusJakarta.variable} ${inter.variable} ${geistMono.variable} antialiased bg-sidebar`}
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

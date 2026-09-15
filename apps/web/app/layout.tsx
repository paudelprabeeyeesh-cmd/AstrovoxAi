import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Providers } from "@/components/shared/providers";
import { SiteHeader } from "@/components/layout/site-header";
import { SiteFooter } from "@/components/layout/site-footer";
import "./globals.css";
const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });
export const metadata: Metadata = {
  title: {
    default: "AstrovoxAI - AI-Powered Chat & Memory Platform",
    template: "%s | AstrovoxAI",
  },
  description: "AstrovoxAI is an AI-powered chat and memory platform that helps you search, organize, and interact with your knowledge using advanced LLMs.",
  keywords: ["AI", "chat", "memory", "knowledge management", "LLM", "conversations", "RAG", "embeddings"],
  authors: [{ name: "AstrovoxAI" }],
  creator: "AstrovoxAI",
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://astrovox.ai",
    title: "AstrovoxAI - AI-Powered Chat & Memory Platform",
    description: "AI-powered chat and memory platform",
    siteName: "AstrovoxAI",
  },
  twitter: {
    card: "summary_large_image",
    title: "AstrovoxAI - AI-Powered Chat & Memory Platform",
    description: "AI-powered chat and memory platform",
    creator: "@astrovoxai",
  },
};
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.variable}>
        <Providers>
          <div className="flex min-h-screen flex-col">
            <SiteHeader />
            <main className="flex-1">{children}</main>
            <SiteFooter />
          </div>
        </Providers>
      </body>
    </html>
  );
}

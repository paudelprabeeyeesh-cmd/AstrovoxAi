import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Providers } from "@/components/shared/providers";
import { SiteHeader } from "@/components/layout/site-header";
import { SiteFooter } from "@/components/layout/site-footer";
import "./globals.css";
const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });
export const metadata: Metadata = { title: "AstrovoxAI", description: "AI-powered chat and memory platform" };
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

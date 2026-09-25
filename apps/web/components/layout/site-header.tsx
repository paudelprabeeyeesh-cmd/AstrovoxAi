"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
export function SiteHeader() {
  const pathname = usePathname();
  const isAuth = pathname?.startsWith("/login") || pathname?.startsWith("/register") || pathname?.startsWith("/forgot-password") || pathname?.startsWith("/reset-password");
  if (isAuth) return null;
  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
        <Link href="/" className="flex items-center gap-2 font-bold">AstrovoxAI</Link>
        <nav className="hidden md:flex gap-6 text-sm">
          <Link href="/chat" className="text-muted-foreground hover:text-foreground transition">Chat</Link>
          <Link href="/dashboard" className="text-muted-foreground hover:text-foreground transition">Dashboard</Link>
          <Link href="/library" className="text-muted-foreground hover:text-foreground transition">Library</Link>
          <Link href="/pricing" className="text-muted-foreground hover:text-foreground transition">Pricing</Link>
        </nav>
        <div className="flex gap-2">
          <Button variant="ghost" asChild><Link href="/login">Sign In</Link></Button>
          <Button asChild><Link href="/register">Get Started</Link></Button>
        </div>
      </div>
    </header>
  );
}

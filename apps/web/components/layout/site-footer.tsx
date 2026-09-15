import Link from "next/link";
export function SiteFooter() {
  return (
    <footer className="border-t">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 px-6 py-8 md:flex-row md:items-center md:justify-between">
        <p className="text-sm text-muted-foreground"> AstrovoxAI. All rights reserved.</p>
        <div className="flex gap-4 text-sm text-muted-foreground">
          <Link href="/settings/profile" className="hover:text-foreground">Settings</Link>
          <Link href="/privacy" className="hover:text-foreground">Privacy</Link>
          <Link href="/terms" className="hover:text-foreground">Terms</Link>
        </div>
      </div>
    </footer>
  );
}

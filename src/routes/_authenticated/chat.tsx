import { createFileRoute, Outlet } from "@tanstack/react-router";
import { useState } from "react";
import { Menu } from "lucide-react";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { AstroWordmark } from "@/components/brand/Logo";

export const Route = createFileRoute("/_authenticated/chat")({
  component: ChatLayout,
});

function ChatLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  return (
    <div className="flex h-screen min-h-0 w-full bg-background text-foreground">
      <ChatSidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <main className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center justify-between border-b border-border/60 px-4 py-2 md:hidden">
          <button
            onClick={() => setSidebarOpen(true)}
            aria-label="Open menu"
            className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <Menu className="h-5 w-5" />
          </button>
          <AstroWordmark className="scale-90" />
          <span className="w-7" />
        </div>
        <div className="min-h-0 flex-1">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
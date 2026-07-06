import { Link, useNavigate, useParams } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useServerFn } from "@tanstack/react-start";
import {
  Plus,
  Search,
  MessageSquare,
  Trash2,
  Pencil,
  LogOut,
  Settings,
  X,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { supabase } from "@/integrations/supabase/client";
import { toast } from "sonner";
import {
  createConversation,
  deleteConversation,
  listConversations,
  renameConversation,
} from "@/lib/conversations.functions";
import { AstroWordmark } from "@/components/brand/Logo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export const conversationsQueryKey = ["conversations"] as const;

export function ChatSidebar({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  const params = useParams({ strict: false }) as { threadId?: string };
  const activeId = params.threadId;
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");

  const listFn = useServerFn(listConversations);
  const createFn = useServerFn(createConversation);
  const deleteFn = useServerFn(deleteConversation);
  const renameFn = useServerFn(renameConversation);

  const { data: conversations = [] } = useQuery({
    queryKey: conversationsQueryKey,
    queryFn: () => listFn(),
  });

  const filtered = useMemo(() => {
    if (!search.trim()) return conversations;
    const q = search.toLowerCase();
    return conversations.filter((c) => (c.title ?? "").toLowerCase().includes(q));
  }, [conversations, search]);

  const createMutation = useMutation({
    mutationFn: () => createFn({ data: {} }),
    onSuccess: async (row) => {
      await qc.invalidateQueries({ queryKey: conversationsQueryKey });
      onClose();
      void navigate({ to: "/chat/$threadId", params: { threadId: row.id } });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Failed to create"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteFn({ data: { id } }),
    onSuccess: async (_d, id) => {
      await qc.invalidateQueries({ queryKey: conversationsQueryKey });
      if (activeId === id) void navigate({ to: "/chat" });
      toast.success("Conversation deleted");
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Failed to delete"),
  });

  const renameMutation = useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) =>
      renameFn({ data: { id, title } }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: conversationsQueryKey });
      setEditingId(null);
      toast.success("Renamed");
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Rename failed"),
  });

  async function handleSignOut() {
    await qc.cancelQueries();
    qc.clear();
    await supabase.auth.signOut();
    void navigate({ to: "/auth", replace: true });
  }

  const content = (
    <div className="flex h-full flex-col bg-sidebar text-sidebar-foreground">
      <div className="flex items-center justify-between px-4 pt-4">
        <Link to="/" aria-label="Home">
          <AstroWordmark />
        </Link>
        <button
          onClick={onClose}
          className="rounded-md p-1 text-muted-foreground hover:bg-sidebar-accent md:hidden"
          aria-label="Close sidebar"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="px-3 pt-4">
        <Button
          onClick={() => createMutation.mutate()}
          disabled={createMutation.isPending}
          className="w-full justify-start gap-2 bg-aurora text-primary-foreground shadow-md shadow-primary/20 hover:opacity-90"
        >
          <Plus className="h-4 w-4" /> New conversation
        </Button>
      </div>

      <div className="px-3 pt-3">
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search conversations"
            className="h-9 border-sidebar-border bg-sidebar-accent/40 pl-8 text-sm placeholder:text-muted-foreground"
          />
        </div>
      </div>

      <nav className="thin-scroll mt-3 flex-1 overflow-y-auto px-2 pb-2">
        {filtered.length === 0 ? (
          <div className="px-3 py-6 text-center text-xs text-muted-foreground">
            {search ? "No matches" : "No conversations yet"}
          </div>
        ) : (
          <ul className="space-y-0.5">
            {filtered.map((c) => {
              const isActive = c.id === activeId;
              const isEditing = editingId === c.id;
              return (
                <li key={c.id}>
                  <div
                    className={cn(
                      "group flex items-center gap-2 rounded-lg px-2 py-2 text-sm transition-colors",
                      isActive
                        ? "bg-sidebar-accent text-sidebar-accent-foreground"
                        : "hover:bg-sidebar-accent/60",
                    )}
                  >
                    <MessageSquare className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                    {isEditing ? (
                      <input
                        autoFocus
                        value={editingTitle}
                        onChange={(e) => setEditingTitle(e.target.value)}
                        onBlur={() => {
                          if (editingTitle.trim() && editingTitle !== c.title) {
                            renameMutation.mutate({ id: c.id, title: editingTitle.trim() });
                          } else {
                            setEditingId(null);
                          }
                        }}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") (e.target as HTMLInputElement).blur();
                          if (e.key === "Escape") setEditingId(null);
                        }}
                        className="flex-1 bg-transparent text-sm outline-none"
                      />
                    ) : (
                      <Link
                        to="/chat/$threadId"
                        params={{ threadId: c.id }}
                        onClick={onClose}
                        className="flex-1 truncate"
                      >
                        {c.title || "Untitled"}
                      </Link>
                    )}
                    {!isEditing && (
                      <div className="hidden items-center gap-1 group-hover:flex">
                        <button
                          aria-label="Rename"
                          onClick={() => {
                            setEditingId(c.id);
                            setEditingTitle(c.title || "");
                          }}
                          className="rounded p-1 text-muted-foreground hover:text-foreground"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </button>
                        <button
                          aria-label="Delete"
                          onClick={() => {
                            if (confirm("Delete this conversation?")) deleteMutation.mutate(c.id);
                          }}
                          className="rounded p-1 text-muted-foreground hover:text-destructive"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </nav>

      <div className="border-t border-sidebar-border p-2">
        <Link
          to="/settings"
          onClick={onClose}
          className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
        >
          <Settings className="h-4 w-4" /> Settings
        </Link>
        <button
          onClick={handleSignOut}
          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
        >
          <LogOut className="h-4 w-4" /> Sign out
        </button>
      </div>
    </div>
  );

  return (
    <>
      {/* desktop */}
      <aside className="hidden w-72 shrink-0 border-r border-sidebar-border md:block">
        {content}
      </aside>
      {/* mobile drawer */}
      <AnimatePresence>
        {open && (
          <>
            <motion.div
              key="bk"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={onClose}
              className="fixed inset-0 z-40 bg-background/70 backdrop-blur-sm md:hidden"
            />
            <motion.aside
              key="dr"
              initial={{ x: -300 }}
              animate={{ x: 0 }}
              exit={{ x: -300 }}
              transition={{ type: "spring", stiffness: 320, damping: 32 }}
              className="fixed inset-y-0 left-0 z-50 w-72 border-r border-sidebar-border md:hidden"
            >
              {content}
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
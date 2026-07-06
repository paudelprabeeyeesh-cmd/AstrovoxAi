import { useEffect, useRef, useState } from "react";
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport, type UIMessage } from "ai";
import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { ArrowUp, RefreshCw, Square, User, Copy, Check, PencilLine } from "lucide-react";
import { AstroMark } from "@/components/brand/Logo";
import { Markdown } from "@/components/chat/Markdown";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { supabase } from "@/integrations/supabase/client";
import { toast } from "sonner";
import { ASTROVOX_MODELS, DEFAULT_MODEL, normalizeModelId, type AstrovoxModelId } from "@/lib/ai-gateway.server";
import { conversationsQueryKey } from "@/components/chat/ChatSidebar";

const SUGGESTIONS = [
  "Explain transformers like I'm a senior engineer",
  "Draft a polite follow-up email to a client",
  "Help me debug this TypeScript error",
  "Brainstorm 5 startup ideas in climate tech",
];

function extractText(m: UIMessage): string {
  return (m.parts ?? [])
    .map((p) =>
      p && typeof p === "object" && "type" in p && p.type === "text"
        ? (p as { text: string }).text
        : "",
    )
    .join("");
}

export function ChatWindow({
  threadId,
  initialMessages,
  initialModel,
}: {
  threadId: string | null;
  initialMessages: UIMessage[];
  initialModel?: AstrovoxModelId;
}) {
  const [input, setInput] = useState("");
  const [model, setModel] = useState<AstrovoxModelId>(() => normalizeModelId(initialModel ?? DEFAULT_MODEL));
  const scrollRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);
  const tokenRef = useRef<string | null>(null);
  const qc = useQueryClient();
  const navigate = useNavigate();

  useEffect(() => {
    void supabase.auth.getSession().then(({ data }) => {
      tokenRef.current = data.session?.access_token ?? null;
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => {
      tokenRef.current = s?.access_token ?? null;
    });
    return () => sub.subscription.unsubscribe();
  }, []);

  const transport = new DefaultChatTransport({
    api: "/api/chat",
    headers: async (): Promise<Record<string, string>> => {
      let t = tokenRef.current;
      if (!t) {
        const { data } = await supabase.auth.getSession();
        t = data.session?.access_token ?? null;
        tokenRef.current = t;
      }
      return t ? { Authorization: `Bearer ${t}` } : {};
    },
    body: () => ({ model, conversationId: threadId }),
  });

  const { messages, sendMessage, status, stop, regenerate, setMessages, error } = useChat({
    id: threadId ?? "new",
    messages: initialMessages,
    transport,
    onError: (e) => {
      const msg = e.message || "Something went wrong";
      if (/unauthor/i.test(msg) || /401/.test(msg)) {
        toast.error("Your session expired — please sign in again.");
        void navigate({ to: "/auth" });
        return;
      }
      toast.error(msg);
    },
    onFinish: () => {
      void qc.invalidateQueries({ queryKey: conversationsQueryKey });
    },
  });

  const isLoading = status === "submitted" || status === "streaming";

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, status]);

  useEffect(() => {
    taRef.current?.focus();
  }, [threadId]);

  async function handleSend(text: string) {
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;
    setInput("");
    await sendMessage({ text: trimmed });
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend(input);
    }
  }

  function handleEdit(index: number, newText: string) {
    const truncated = messages.slice(0, index);
    setMessages(truncated);
    void sendMessage({ text: newText });
  }

  const empty = messages.length === 0;

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* model picker */}
      <div className="flex items-center justify-end gap-2 border-b border-border/60 px-4 py-2">
        <label className="text-xs text-muted-foreground">Model</label>
        <select
          value={model}
          onChange={(e) => setModel(e.target.value as AstrovoxModelId)}
          className="rounded-md border border-border bg-card px-2 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
        >
          {ASTROVOX_MODELS.map((m) => (
            <option key={m.id} value={m.id}>
              {m.label}
            </option>
          ))}
        </select>
      </div>

      <div ref={scrollRef} className="thin-scroll flex-1 overflow-y-auto">
        {empty ? (
          <EmptyState onPick={(s) => handleSend(s)} />
        ) : (
          <div className="mx-auto max-w-3xl px-4 py-8">
            {messages.map((m, i) => (
              <MessageRow
                key={m.id}
                message={m}
                isLast={i === messages.length - 1}
                streaming={status === "streaming" && i === messages.length - 1 && m.role === "assistant"}
                onEdit={(text) => handleEdit(i, text)}
              />
            ))}
            {status === "submitted" && messages[messages.length - 1]?.role === "user" && (
              <div className="mt-4 flex items-start gap-3">
                <AstroMark className="mt-1 h-6 w-6" />
                <div className="text-sm text-muted-foreground">
                  <span className="inline-flex items-center gap-1">
                    <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
                    Thinking…
                  </span>
                </div>
              </div>
            )}
            {error && (
              <div className="mt-4 rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive-foreground">
                {error.message}
              </div>
            )}
          </div>
        )}
      </div>

      {/* composer */}
      <div className="border-t border-border/60 bg-background/60 px-4 py-4 backdrop-blur">
        <div className="mx-auto max-w-3xl">
          <div className="surface-glass flex items-end gap-2 rounded-2xl px-3 py-2 focus-within:border-accent/60 focus-within:ring-1 focus-within:ring-accent/30">
            <textarea
              ref={taRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              placeholder="Message AstrovoxAI…"
              className="thin-scroll max-h-40 flex-1 resize-none bg-transparent py-2 text-sm leading-6 outline-none placeholder:text-muted-foreground"
              style={{ minHeight: "2.5rem" }}
            />
            {isLoading ? (
              <Button
                size="icon"
                variant="secondary"
                onClick={() => stop()}
                className="h-9 w-9 shrink-0 rounded-full"
                aria-label="Stop generation"
              >
                <Square className="h-4 w-4" />
              </Button>
            ) : (
              <Button
                size="icon"
                onClick={() => handleSend(input)}
                disabled={!input.trim()}
                className="h-9 w-9 shrink-0 rounded-full bg-aurora text-primary-foreground disabled:opacity-40"
                aria-label="Send message"
              >
                <ArrowUp className="h-4 w-4" />
              </Button>
            )}
          </div>
          <div className="mt-2 flex items-center justify-between text-[11px] text-muted-foreground">
            <span>Press Enter to send · Shift+Enter for newline</span>
            {messages.length > 0 && !isLoading && (
              <button
                type="button"
                onClick={() => regenerate()}
                className="inline-flex items-center gap-1 hover:text-foreground"
              >
                <RefreshCw className="h-3 w-3" /> Regenerate
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function EmptyState({ onPick }: { onPick: (s: string) => void }) {
  return (
    <div className="mx-auto flex h-full max-w-2xl flex-col items-center justify-center px-6 py-12 text-center">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="flex flex-col items-center"
      >
        <AstroMark className="h-12 w-12" />
        <h1
          className="mt-5 text-3xl font-semibold tracking-tight"
          style={{ fontFamily: "var(--font-display)" }}
        >
          How can I help today?
        </h1>
        <p className="mt-2 max-w-md text-sm text-muted-foreground">
          Ask AstrovoxAI anything — I stream answers in real time and remember our conversation.
        </p>
        <div className="mt-8 grid w-full gap-2 sm:grid-cols-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => onPick(s)}
              className="surface-glass rounded-xl px-4 py-3 text-left text-sm text-foreground/90 transition hover:border-accent/40"
            >
              {s}
            </button>
          ))}
        </div>
      </motion.div>
    </div>
  );
}

function MessageRow({
  message,
  isLast,
  streaming,
  onEdit,
}: {
  message: UIMessage;
  isLast: boolean;
  streaming: boolean;
  onEdit: (text: string) => void;
}) {
  const text = extractText(message);
  const [copied, setCopied] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(text);

  if (message.role === "user") {
    return (
      <div className="group mb-6 flex justify-end">
        <div className="max-w-[85%]">
          <div className="flex items-start justify-end gap-2">
            <div className="rounded-2xl rounded-tr-sm bg-primary px-4 py-2.5 text-sm leading-6 text-primary-foreground shadow-md shadow-primary/20">
              {editing ? (
                <div className="flex flex-col gap-2">
                  <textarea
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    rows={3}
                    className="w-72 resize-y rounded-md bg-background p-2 text-sm text-foreground outline-none"
                  />
                  <div className="flex justify-end gap-2">
                    <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>
                      Cancel
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => {
                        const t = draft.trim();
                        if (t) {
                          setEditing(false);
                          onEdit(t);
                        }
                      }}
                    >
                      Send
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="whitespace-pre-wrap">{text}</div>
              )}
            </div>
            <User className="mt-1 h-5 w-5 shrink-0 text-muted-foreground" />
          </div>
          {!editing && (
            <div className="mt-1 flex justify-end gap-2 pr-7 text-xs text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100">
              <button
                onClick={() => {
                  setDraft(text);
                  setEditing(true);
                }}
                className="inline-flex items-center gap-1 hover:text-foreground"
              >
                <PencilLine className="h-3 w-3" /> Edit
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="group mb-6 flex items-start gap-3">
      <AstroMark className="mt-1 h-6 w-6 shrink-0" />
      <div className="min-w-0 flex-1">
        <div className={cn("min-w-0", streaming && "streaming-caret")}>
          {text ? <Markdown content={text} /> : <span className="text-muted-foreground">…</span>}
        </div>
        {isLast && !streaming && text && (
          <div className="mt-2 flex gap-2 text-xs text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100">
            <button
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(text);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 1500);
                } catch {
                  /* noop */
                }
              }}
              className="inline-flex items-center gap-1 hover:text-foreground"
            >
              {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
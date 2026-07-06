import { createFileRoute, useParams } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useServerFn } from "@tanstack/react-start";
import type { UIMessage } from "ai";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { getConversationWithMessages } from "@/lib/conversations.functions";
import type { AstrovoxModelId } from "@/lib/ai-gateway.server";
import { Loader2 } from "lucide-react";

export const Route = createFileRoute("/_authenticated/chat/$threadId")({
  component: ThreadPage,
});

type DbMessage = {
  id: string;
  role: string;
  content: string;
  parts: unknown;
  created_at: string;
};

function toUIMessages(rows: DbMessage[]): UIMessage[] {
  return rows.map((r) => ({
    id: r.id,
    role: r.role === "assistant" ? "assistant" : r.role === "system" ? "system" : "user",
    parts: [{ type: "text", text: r.content }],
  })) as UIMessage[];
}

function ThreadPage() {
  const { threadId } = useParams({ from: "/_authenticated/chat/$threadId" });
  const loadFn = useServerFn(getConversationWithMessages);
  const { data, isLoading, error } = useQuery({
    queryKey: ["conversation", threadId],
    queryFn: () => loadFn({ data: { id: threadId } }),
  });

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" />
      </div>
    );
  }
  if (error || !data) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-destructive-foreground">
        Could not load this conversation.
      </div>
    );
  }

  return (
    <ChatWindow
      key={threadId}
      threadId={threadId}
      initialMessages={toUIMessages(data.messages as DbMessage[])}
      initialModel={data.conversation.model as AstrovoxModelId}
    />
  );
}
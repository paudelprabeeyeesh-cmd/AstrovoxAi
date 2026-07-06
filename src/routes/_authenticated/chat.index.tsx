import { createFileRoute } from "@tanstack/react-router";
import { ChatWindow } from "@/components/chat/ChatWindow";

export const Route = createFileRoute("/_authenticated/chat/")({
  component: NewChat,
});

function NewChat() {
  // No threadId yet — sending will create one server-side via /api/chat,
  // but we want history persistence too. So creating a conversation happens
  // when the user clicks "New conversation". For an unsaved chat just render an empty window.
  return <ChatWindow threadId={null} initialMessages={[]} />;
}
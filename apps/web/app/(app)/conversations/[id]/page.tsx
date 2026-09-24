'use client';

import { useParams, useRouter } from 'next/navigation';
import { use, useEffect, useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { MessageSquarePlus, Search, FolderPlus, Pin, PinOff } from 'lucide-react';
import { ChatContainer } from '@/components/chat/chat-container';
import { useChat } from '@/lib/hooks/use-chat';
import { useChatStore } from '@/lib/store/chat-store';
import { cn } from '@/lib/utils';

const MOCK_CONVERSATIONS = [
  { id: '1', title: 'React Hooks deep dive', pinned: true, folder: null },
  { id: '2', title: 'Tailwind migration plan', pinned: false, folder: 'Work' },
  { id: '3', title: 'Database schema review', pinned: false, folder: null },
];

export default function ConversationByIdPage() {
  const params = useParams();
  const router = useRouter();
  const [isClient, setIsClient] = useState(false);

  const id = typeof params.id === 'string' ? params.id : Array.isArray(params.id) ? params.id[0] : '';

  useEffect(() => {
    setIsClient(true);
  }, []);

  if (!isClient) {
    return (
      <div className="flex h-full">
        <div className="flex flex-1 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      </div>
    );
  }

  return (
    <ConversationShell
      conversationId={id}
      router={router}
    />
  );
}

function ConversationShell({
  conversationId,
  router,
}: {
  conversationId: string;
  router: ReturnType<typeof useRouter>;
}) {
  const {
    messages,
    isLoading,
    streamingMessageId,
    error,
    sendMessageStream,
    stopStreaming,
    regenerateMessage,
    editMessage,
    copyMessage,
    rateMessage,
  } = useChat();
  const { conversations, setActiveConversation, pinConversation, unpinConversation, moveConversationToFolder, createFolder } = useChatStore();

  const conversation = conversations.find((c) => c.id === conversationId) ?? MOCK_CONVERSATIONS.find((c) => c.id === conversationId);

  const handleSendMessage = async (content: string, options?: { imageUrl?: string }) => {
    sendMessageStream(content, 'gpt-4', options?.imageUrl);
  };

  const handleSelectConversation = (nextId: string) => {
    setActiveConversation(nextId);
    router.push(`/chat/${nextId}`);
  };

  return (
    <div className="flex h-full">
      <div className="flex h-full w-64 flex-col border-r border-border bg-muted/40">
        <div className="flex h-14 items-center justify-between px-3">
          <span className="font-semibold text-sm">Conversations</span>
          <Button
            variant="ghost"
            size="icon"
            className="size-8"
            onClick={() => router.push('/chat')}
            title="Back to conversations"
          >
            <MessageSquarePlus className="size-4" />
          </Button>
        </div>

        <ScrollArea className="flex-1 px-2 py-1">
          {conversation && (
            <div className="rounded-md border border-dashed border-primary/40 bg-primary/5 p-3">
              <p className="text-xs font-medium mb-1">Current</p>
              <p className="text-xs truncate">{conversation.title}</p>
              <Badge variant="secondary" className="text-[10px] mt-2">
                {conversation.id}
              </Badge>
            </div>
          )}
          <div className="mt-4 space-y-2">
            {MOCK_CONVERSATIONS.map((conv) => (
              <Button
                key={conv.id}
                variant="ghost"
                className="w-full justify-start"
                onClick={() => handleSelectConversation(conv.id)}
              >
                <MessageSquarePlus className="mr-2 size-4" />
                <span className="truncate text-left">{conv.title}</span>
              </Button>
            ))}
          </div>
        </ScrollArea>
      </div>

      <div className="flex flex-1 flex-col">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div>
            <h1 className="text-sm font-semibold truncate">
              {conversation?.title ?? 'Conversation'}
            </h1>
            <p className="text-xs text-muted-foreground">
              ID: {conversationId}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {conversation && (
              <Badge variant="outline" className="text-xs">
                {conversation.pinned ? 'Pinned' : 'Open'}
              </Badge>
            )}
          </div>
        </div>

        <ChatContainer
          messages={messages}
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
          isStreaming={!!streamingMessageId}
          streamingMessageId={streamingMessageId}
          onStopStreaming={stopStreaming}
          onRegenerate={regenerateMessage}
          onEdit={editMessage}
          onCopy={copyMessage}
          onFeedback={rateMessage}
          error={error}
          selectedModel="gpt-4"
          onModelChange={() => {}}
        />
      </div>
    </div>
  );
}

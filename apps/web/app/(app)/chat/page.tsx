'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { ChatContainer } from '@/components/chat/chat-container';
import { useChat } from '@/lib/hooks/use-chat';
import { useChatStore } from '@/lib/store/chat-store';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { MessageSquarePlus, Search, FolderPlus, Pin, PinOff } from 'lucide-react';

export default function NewChatPage() {
  const router = useRouter();
  const [isClient, setIsClient] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);

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
    <div className="flex h-full">
      <EnhancedChatWrapper
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        selectedFolder={selectedFolder}
        setSelectedFolder={setSelectedFolder}
      />
    </div>
  );
}

function EnhancedChatWrapper({
  searchQuery,
  setSearchQuery,
  selectedFolder,
  setSelectedFolder,
}: {
  searchQuery: string
  setSearchQuery: (query: string) => void
  selectedFolder: string | null
  setSelectedFolder: (folder: string | null) => void
}) {
  const router = useRouter();
  const { conversations, activeId, setActiveConversation, pinConversation, unpinConversation, moveConversationToFolder, createFolder } = useChatStore();
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

  const handleNewChat = useCallback(() => {
    const newId = crypto.randomUUID();
    router.push(`/chat/${newId}`);
  }, [router]);

  const handleSelectConversation = useCallback(
    (id: string) => {
      setActiveConversation(id);
      router.push(`/chat/${id}`);
    },
    [router, setActiveConversation]
  );

  const handlePinConversation = useCallback(
    (id: string, pinned: boolean) => {
      if (pinned) {
        unpinConversation(id);
      } else {
        pinConversation(id);
      }
    },
    [pinConversation, unpinConversation]
  );

  const handleMoveToFolder = useCallback(
    (id: string, folder: string) => {
      moveConversationToFolder(id, folder);
    },
    [moveConversationToFolder]
  );

  const handleCreateFolder = useCallback(
    (name: string) => {
      createFolder(name);
    },
    [createFolder]
  );

  const filteredConversations = conversations.filter((conv) => {
    const matchesSearch = !searchQuery || conv.title.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFolder = !selectedFolder || conv.folder === selectedFolder;
    return matchesSearch && matchesFolder;
  });

  const pinnedConversations = filteredConversations.filter((conv) => conv.pinned);
  const otherConversations = filteredConversations.filter((conv) => !conv.pinned);

  return (
    <>
      <div className="flex h-full w-64 flex-col border-r border-border bg-muted/40">
        <div className="flex h-14 items-center justify-between px-3">
          <span className="font-semibold text-sm">Conversations</span>
          <Button variant="ghost" size="icon" className="size-8" onClick={handleNewChat} title="New chat">
            <MessageSquarePlus className="size-4" />
          </Button>
        </div>

        <div className="px-2 pb-2 space-y-2">
          <div className="relative">
            <Search className="absolute left-2 top-2.5 size-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search conversations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-md border border-input bg-background pl-8 pr-3 py-2 text-sm"
            />
          </div>
          <div className="flex gap-1">
            <Button
              variant={selectedFolder === null ? 'default' : 'outline'}
              size="sm"
              className="flex-1"
              onClick={() => setSelectedFolder(null)}
            >
              All
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={() => {
                const name = prompt('Folder name');
                if (name) {
                  handleCreateFolder(name);
                  setSelectedFolder(name);
                }
              }}
            >
              <FolderPlus className="size-3 mr-1" />
              New Folder
            </Button>
          </div>
        </div>

        <ScrollArea className="flex-1 px-2 py-1">
          {pinnedConversations.length > 0 && (
            <div className="mb-2">
              <div className="text-xs font-medium text-muted-foreground px-2 py-1">Pinned</div>
              {pinnedConversations.map((conv) => (
                <ConversationItem
                  key={conv.id}
                  conversation={conv}
                  isActive={conv.id === activeId}
                  onClick={() => handleSelectConversation(conv.id)}
                  onPin={() => handlePinConversation(conv.id, conv.pinned ?? false)}
                  onMoveToFolder={handleMoveToFolder}
                />
              ))}
            </div>
          )}
          <div>
            <div className="text-xs font-medium text-muted-foreground px-2 py-1">Recent</div>
            {otherConversations.map((conv) => (
              <ConversationItem
                key={conv.id}
                conversation={conv}
                isActive={conv.id === activeId}
                onClick={() => handleSelectConversation(conv.id)}
                onPin={() => handlePinConversation(conv.id, conv.pinned ?? false)}
                onMoveToFolder={handleMoveToFolder}
              />
            ))}
          </div>
        </ScrollArea>
      </div>

      <ChatContainer
        messages={messages}
        onSendMessage={(content, options) => sendMessageStream(content, 'gpt-4', options?.imageUrl)}
        isLoading={isLoading}
        isStreaming={isLoading}
        streamingMessageId={streamingMessageId}
        onStopStreaming={stopStreaming}
        onRegenerate={regenerateMessage}
        onEdit={editMessage}
        onCopy={copyMessage}
        onFeedback={rateMessage}
        error={error}
        selectedModel="gpt-4"
        onModelChange={(model) => console.log('Model changed:', model)}
      />
    </>
  );
}

function ConversationItem({
  conversation,
  isActive,
  onClick,
  onPin,
  onMoveToFolder,
}: {
  conversation: any
  isActive: boolean
  onClick: () => void
  onPin: () => void
  onMoveToFolder: (folder: string) => void
}) {
  return (
    <div
      className={cn(
        'group flex items-center gap-2 rounded-md px-2 py-2 text-sm cursor-pointer transition-colors',
        isActive ? 'bg-accent text-accent-foreground' : 'hover:bg-accent/50'
      )}
      onClick={onClick}
    >
      <MessageSquarePlus className="size-4 shrink-0" />
      <span className="flex-1 truncate">{conversation.title}</span>
      <Button
        variant="ghost"
        size="icon"
        className="size-6 opacity-0 group-hover:opacity-100 transition-opacity"
        onClick={(e) => {
          e.stopPropagation();
          onPin();
        }}
        title={conversation.pinned ? 'Unpin' : 'Pin'}
      >
        {conversation.pinned ? <PinOff className="size-3" /> : <Pin className="size-3" />}
      </Button>
    </div>
  );
}


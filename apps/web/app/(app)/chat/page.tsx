'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { ChatContainer } from '@/components/chat/chat-container';
import { useChat } from '@/lib/hooks/use-chat';
import { useChatStore } from '@/lib/store/chat-store';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  MessageSquarePlus,
  Search,
  FolderPlus,
  Pin,
  PinOff,
  MoreVertical,
  Trash2,
  Archive,
  Download,
  Upload,
  Pencil,
  PanelRightClose,
  PanelRightOpen,
  Settings2,
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Whiteboard } from '@/components/chat/whiteboard';
import { ExportImport } from '@/components/shared/export-import';
import { ChatBranching } from '@/components/chat/chat-branching';
import { VoiceOutput } from '@/components/chat/voice-output';
import { cn } from '@/lib/utils';
import { useSettingsStore } from '@/lib/store/settings-store';

export default function NewChatPage() {
  const router = useRouter();
  const [isClient, setIsClient] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  const [showSidebar, setShowSidebar] = useState(true);
  const [showWhiteboard, setShowWhiteboard] = useState(false);
  const [showBranching, setShowBranching] = useState(false);
  const [showExportImport, setShowExportImport] = useState(false);

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
        showSidebar={showSidebar}
        setShowSidebar={setShowSidebar}
        showWhiteboard={showWhiteboard}
        setShowWhiteboard={setShowWhiteboard}
        showBranching={showBranching}
        setShowBranching={setShowBranching}
        showExportImport={showExportImport}
        setShowExportImport={setShowExportImport}
      />
    </div>
  );
}

function EnhancedChatWrapper({
  searchQuery,
  setSearchQuery,
  selectedFolder,
  setSelectedFolder,
  showSidebar,
  setShowSidebar,
  showWhiteboard,
  setShowWhiteboard,
  showBranching,
  setShowBranching,
  showExportImport,
  setShowExportImport,
}: {
  searchQuery: string
  setSearchQuery: (query: string) => void
  selectedFolder: string | null
  setSelectedFolder: (folder: string | null) => void
  showSidebar: boolean
  setShowSidebar: (show: boolean) => void
  showWhiteboard: boolean
  setShowWhiteboard: (show: boolean) => void
  showBranching: boolean
  setShowBranching: (show: boolean) => void
  showExportImport: boolean
  setShowExportImport: (show: boolean) => void
}) {
  const router = useRouter();
  const { conversations, activeId, setActiveConversation, pinConversation, unpinConversation, createFolder, deleteConversation, archiveConversation } = useChatStore();
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
  const settings = useSettingsStore();

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

  const handleWhiteboardSave = useCallback((dataUrl: string) => {
    console.log('Whiteboard saved:', dataUrl);
  }, []);

  return (
    <>
      {showSidebar && (
        <div className={cn('flex h-full flex-col border-r border-border bg-muted/40 transition-all', showSidebar ? 'w-64' : 'w-0')}>
          <div className="flex h-14 items-center justify-between px-3">
            <span className="font-semibold text-sm">Conversations</span>
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="icon" className="size-8" onClick={handleNewChat} title="New chat">
                <MessageSquarePlus className="size-4" />
              </Button>
              <Button variant="ghost" size="icon" className="size-8" onClick={() => setShowSidebar(false)} title="Close sidebar">
                <PanelRightClose className="size-4" />
              </Button>
            </div>
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
                    onDelete={() => deleteConversation(conv.id)}
                    onArchive={() => archiveConversation(conv.id)}
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
                  onDelete={() => deleteConversation(conv.id)}
                  onArchive={() => archiveConversation(conv.id)}
                />
              ))}
            </div>
          </ScrollArea>
        </div>
      )}

      <div className="flex flex-1 flex-col">
        <div className="flex items-center justify-between px-4 py-2 border-b">
          <div className="flex items-center gap-2">
            {!showSidebar && (
              <Button variant="ghost" size="icon" onClick={() => setShowSidebar(true)} title="Open sidebar">
                <PanelRightOpen className="size-4" />
              </Button>
            )}
            <span className="text-sm font-medium">
              {activeId ? conversations.find((c) => c.id === activeId)?.title || 'Chat' : 'New Chat'}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowWhiteboard(!showWhiteboard)}
              className={showWhiteboard ? 'text-primary' : ''}
            >
              <Pencil className="h-4 w-4 mr-1" />
              Whiteboard
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowBranching(!showBranching)}
              className={showBranching ? 'text-primary' : ''}
            >
              <MessageSquarePlus className="h-4 w-4 mr-1" />
              Branching
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowExportImport(!showExportImport)}
              className={showExportImport ? 'text-primary' : ''}
            >
              <Download className="h-4 w-4 mr-1" />
              Export
            </Button>
          </div>
        </div>

        <div className="flex flex-1 overflow-hidden">
          <div className="flex-1 flex flex-col min-w-0">
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
              selectedModel={settings.modelId || 'gpt-4'}
              onModelChange={(model) => console.log('Model changed:', model)}
            />
          </div>

          {showWhiteboard && (
            <div className="w-[500px] border-l border-border bg-muted/20 overflow-y-auto">
              <Whiteboard onSave={handleWhiteboardSave} />
            </div>
          )}

          {showBranching && (
            <div className="w-[400px] border-l border-border bg-muted/20 overflow-y-auto p-4">
              <ChatBranching conversationId={activeId || ''} />
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function ConversationItem({
  conversation,
  isActive,
  onClick,
  onPin,
  onDelete,
  onArchive,
}: {
  conversation: any
  isActive: boolean
  onClick: () => void
  onPin: () => void
  onDelete: () => void
  onArchive: () => void
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
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="size-6 opacity-0 group-hover:opacity-100 transition-opacity"
            onClick={(e) => e.stopPropagation()}
          >
            <MoreVertical className="size-3" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={(e: React.MouseEvent) => { e.stopPropagation(); onPin(); }}>
            <Pin className="mr-2 h-4 w-4" />
            {conversation.pinned ? 'Unpin' : 'Pin'}
          </DropdownMenuItem>
          <DropdownMenuItem onClick={(e: React.MouseEvent) => { e.stopPropagation(); onArchive(); }}>
            <Archive className="mr-2 h-4 w-4" />
            Archive
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={(e: React.MouseEvent) => { e.stopPropagation(); onDelete(); }} className="text-destructive">
            <Trash2 className="mr-2 h-4 w-4" />
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}

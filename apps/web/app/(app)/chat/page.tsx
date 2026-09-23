'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ChatContainer } from '@/components/chat/chat-container';
import { Message } from '@/components/chat/types';
import { useChat } from '@/lib/hooks/use-chat';
import { ScrollArea } from '@/components/ui/scroll-area';

export default function NewChatPage() {
  const router = useRouter();
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  return (
    <div className="flex h-full">
      {isClient ? (
        <EnhancedChat />
      ) : (
        <div className="flex flex-1 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      )}
    </div>
  );
}

function EnhancedChat() {
  const router = useRouter();
  const {
    messages,
    activeId,
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

  const handleSendMessage = async (content: string, options?: { imageUrl?: string; files?: File[] }) => {
    if (!activeId) {
      const newId = crypto.randomUUID();
      router.push(`/chat/${newId}`);
      setTimeout(() => sendMessageStream(content, 'gpt-4', options?.imageUrl), 100);
      return
    }
    sendMessageStream(content, 'gpt-4', options?.imageUrl);
  };

  const handleStopStreaming = () => {
    stopStreaming();
  };

  const handleRegenerate = (messageId: string) => {
    regenerateMessage(messageId);
  };

  const handleEdit = (messageId: string, content: string) => {
    editMessage(messageId, content);
  };

  const handleCopy = async (content: string) => {
    await copyMessage(content);
  };

  const handleFeedback = (messageId: string, feedback: 'up' | 'down' | null) => {
    rateMessage(messageId, feedback);
  };

  return (
    <ChatContainer
      messages={messages}
      onSendMessage={handleSendMessage}
      isLoading={isLoading}
      isStreaming={isLoading}
      streamingMessageId={streamingMessageId}
      onStopStreaming={handleStopStreaming}
      onRegenerate={handleRegenerate}
      onEdit={handleEdit}
      onCopy={handleCopy}
      onFeedback={handleFeedback}
      error={error}
      selectedModel="gpt-4"
      onModelChange={(model) => console.log('Model changed:', model)}
    />
  );
}

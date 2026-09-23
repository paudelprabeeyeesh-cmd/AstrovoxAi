'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { ChatContainer } from '@/components/chat/chat-container';
import { useChat } from '@/lib/hooks/use-chat';
import { useChatStore } from '@/lib/store/chat-store';

export default function ConversationPage() {
  const params = useParams();
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  return (
    <div className="flex h-full">
      {isClient ? (
        <EnhancedChat conversationId={params.id as string} />
      ) : (
        <div className="flex flex-1 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      )}
    </div>
  );
}

function EnhancedChat({ conversationId }: { conversationId: string }) {
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

  useEffect(() => {
    if (activeId !== conversationId) {
      const { setActiveConversation, setMessages } = useChatStore.getState()
      setActiveConversation(conversationId)
      setMessages(conversationId, [])
    }
  }, [conversationId, activeId])

  const handleSendMessage = async (content: string, options?: { imageUrl?: string; files?: File[] }) => {
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

'use client'
import { Message } from './types'
import { EmptyState } from './empty-state'
import { MessageList } from './message-list'
import { Composer } from './composer'
import { AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface ChatContainerProps {
  messages: Message[]
  onSendMessage: (content: string, options?: { imageUrl?: string; files?: File[] }) => void
  isLoading?: boolean
  isStreaming?: boolean
  streamingMessageId?: string | null
  selectedModel?: string
  onModelChange?: (model: string) => void
  onStopStreaming?: () => void
  error?: Error | null
  onRetry?: () => void
  onRegenerate?: (messageId: string) => void
  onEdit?: (messageId: string, content: string) => void
  onCopy?: (content: string) => void
  onFeedback?: (messageId: string, feedback: 'up' | 'down' | null) => void
}

export function ChatContainer({
  messages,
  onSendMessage,
  isLoading,
  isStreaming,
  streamingMessageId,
  selectedModel,
  onModelChange,
  onStopStreaming,
  error,
  onRetry,
  onRegenerate,
  onEdit,
  onCopy,
  onFeedback,
}: ChatContainerProps) {
  const isStreamingActive = isStreaming || isLoading

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-hidden">
        {messages.length === 0 ? (
          <EmptyState onSuggestionClick={(prompt) => onSendMessage(prompt)} />
        ) : (
          <>
            {error && (
              <div className="mx-auto max-w-3xl px-4 pt-4">
                <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950/30 p-4">
                  <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-red-900 dark:text-red-100">
                      Something went wrong
                    </p>
                    <p className="text-xs text-red-700 dark:text-red-300 mt-1">{error.message}</p>
                  </div>
                  {onRetry && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={onRetry}
                      className="border-red-300 hover:bg-red-100 dark:border-red-700 dark:hover:bg-red-900/30"
                    >
                      Retry
                    </Button>
                  )}
                </div>
              </div>
            )}

            <MessageList
              messages={messages}
              isTyping={isStreamingActive && !streamingMessageId}
            />
          </>
        )}
      </div>

      <Composer
        onSend={onSendMessage}
        isLoading={isStreamingActive}
        onStop={onStopStreaming}
        selectedModel={selectedModel}
        onModelChange={onModelChange}
      />
    </div>
  )
}

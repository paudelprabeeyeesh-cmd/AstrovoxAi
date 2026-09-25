'use client'
import { useEffect, useRef } from 'react'
import { Message } from './types'
import { MessageBubble } from './message-bubble'
import { TypingIndicator } from './typing-indicator'
import { StreamingMessage } from './streaming-message'
import { ScrollArea } from '@/components/ui/scroll-area'

interface MessageListProps {
  messages: Message[]
  isTyping?: boolean
  streamingMessageId?: string | null
  onRegenerate?: (messageId: string) => void
  onEdit?: (messageId: string, content: string) => void
  onCopy?: (content: string) => void
  onFeedback?: (messageId: string, feedback: 'up' | 'down' | null) => void
  onStop?: () => void
}

export function MessageList({
  messages,
  isTyping,
  streamingMessageId,
  onRegenerate,
  onEdit,
  onCopy,
  onFeedback,
  onStop,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isTyping || streamingMessageId) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  }, [messages, isTyping, streamingMessageId])

  return (
    <ScrollArea className="h-full w-full" type="auto">
      <div className="mx-auto max-w-3xl px-4 py-6">
        <div className="space-y-6">
          {messages.map((message) => {
            const isStreaming = message.id === streamingMessageId && message.isStreaming

            if (isStreaming) {
              return (
                <div key={message.id} className="flex gap-4">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-purple-500 to-pink-500 text-white">
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                    </svg>
                  </div>
                  <div className="flex max-w-[80%] flex-col items-start">
                    <div className="mb-1 flex items-center gap-2">
                      <span className="text-xs font-medium text-foreground">Assistant</span>
                      {message.model && (
                        <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                          {message.model}
                        </span>
                      )}
                    </div>
                    <div className="rounded-2xl bg-muted px-4 py-2.5">
                      <StreamingMessage
                        content={message.content}
                        isStreaming={isStreaming}
                      />
                    </div>
                  </div>
                </div>
              )
            }

            return (
              <MessageBubble
                key={message.id}
                message={message}
                onRegenerate={onRegenerate}
                onEdit={onEdit}
                onCopy={onCopy}
                onFeedback={onFeedback}
                onStop={onStop}
                isStreaming={isStreaming}
              />
            )
          })}
          {isTyping && <TypingIndicator />}
          <div ref={bottomRef} />
        </div>
      </div>
    </ScrollArea>
  )
}

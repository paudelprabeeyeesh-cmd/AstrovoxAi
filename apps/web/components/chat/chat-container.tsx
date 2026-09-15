'use client'
import { Message } from './types'
import { EmptyState } from './empty-state'
import { MessageList } from './message-list'
import { Composer } from './composer'

interface ChatContainerProps {
  messages: Message[]
  onSendMessage: (content: string) => void
  isLoading?: boolean
  selectedModel?: string
  onModelChange?: (model: string) => void
}

export function ChatContainer({ messages, onSendMessage, isLoading, selectedModel, onModelChange }: ChatContainerProps) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-hidden">
        {messages.length === 0 ? (
          <EmptyState onSuggestionClick={(prompt) => onSendMessage(prompt)} />
        ) : (
          <MessageList messages={messages} />
        )}
      </div>
      <Composer onSend={onSendMessage} isLoading={isLoading} selectedModel={selectedModel} onModelChange={onModelChange} />
    </div>
  )
}

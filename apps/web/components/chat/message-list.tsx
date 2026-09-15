'use client'
import { useEffect, useRef } from 'react'
import { Message } from './types'
import { MessageBubble } from './message-bubble'
import { TypingIndicator } from './typing-indicator'
import { ScrollArea } from '@radix-ui/react-scroll-area'

interface MessageListProps {
  messages: Message[]
  isTyping?: boolean
}

export function MessageList({ messages, isTyping }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  return (
    <ScrollArea className="h-full w-full" type="auto">
      <div className="mx-auto max-w-3xl px-4 py-6">
        <div className="space-y-6">
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
          {isTyping && <TypingIndicator />}
          <div ref={bottomRef} />
        </div>
      </div>
    </ScrollArea>
  )
}

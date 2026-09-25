'use client'
import { useEffect, useRef } from 'react'
import { MarkdownRenderer } from './markdown-renderer'
import { CodeBlock } from './code-block'

interface StreamingMessageProps {
  content: string
  isStreaming?: boolean
  thinking?: boolean
}

export function StreamingMessage({ content, isStreaming = false, thinking = false }: StreamingMessageProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isStreaming) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  }, [content, isStreaming])

  if (thinking) {
    return (
      <div className="flex items-center gap-3 rounded-2xl bg-muted px-4 py-3">
        <div className="flex items-center gap-1">
          <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.3s]" />
          <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.15s]" />
          <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground" />
        </div>
        <span className="text-sm text-muted-foreground">Thinking</span>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-1">
      <MarkdownRenderer content={content} />
      {isStreaming && (
        <>
          <span className="ml-1 inline-block h-4 w-2 animate-pulse bg-primary" />
          <div ref={bottomRef} />
        </>
      )}
    </div>
  )
}

'use client'
import { MarkdownRenderer } from './markdown-renderer'

interface StreamingMessageProps {
  content: string
}

export function StreamingMessage({ content }: StreamingMessageProps) {
  return (
    <div className="flex flex-col gap-1">
      <MarkdownRenderer content={content} />
      <span className="ml-1 inline-block h-4 w-2 animate-pulse bg-primary" />
    </div>
  )
}

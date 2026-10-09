'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Square, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface MessageInputProps {
  onSend: (content: string) => void
  onStop?: () => void
  isLoading?: boolean
  placeholder?: string
  disabled?: boolean
  maxLength?: number
}

export function MessageInput({
  onSend,
  onStop,
  isLoading = false,
  placeholder = 'Type a message...',
  disabled = false,
  maxLength = 128000,
}: MessageInputProps) {
  const [value, setValue] = useState('')
  const [isSending, setIsSending] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const isOverLimit = value.length > maxLength

  const handleSubmit = async () => {
    const trimmed = value.trim()
    if (!trimmed || isLoading || isSending || isOverLimit) return

    setIsSending(true)
    try {
      await onSend(trimmed)
    } finally {
      setIsSending(false)
    }

    setValue('')

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.focus()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`
    }
  }, [value])

  return (
    <div className="border-t bg-background p-4">
      <div className="mx-auto max-w-3xl">
        <div className="flex items-end gap-2 rounded-xl border bg-background p-2 shadow-sm focus-within:ring-2 focus-within:ring-primary/20 transition-all">
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={value}
              onChange={(e) => setValue(e.target.value.slice(0, maxLength))}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              className="w-full resize-none border-0 bg-transparent px-2 py-2 text-sm focus:outline-none focus:ring-0 min-h-[40px] max-h-[200px]"
              rows={1}
              disabled={disabled || isLoading || isSending}
            />
          </div>

          <div className="flex items-center gap-1">
            {isOverLimit && (
              <span className="text-xs text-red-500">Over limit</span>
            )}

            {!isOverLimit && value.length > 0 && (
              <span className="text-xs text-muted-foreground tabular-nums pr-1">
                {value.length.toLocaleString()}
              </span>
            )}

            <Button
              onClick={isLoading ? onStop : handleSubmit}
              className="mb-0.5 mr-0.5 h-8 w-8 shrink-0 p-0"
              disabled={(!value.trim() && !isLoading) || isOverLimit}
              variant={isLoading ? 'destructive' : 'default'}
              title={isLoading ? 'Stop generating' : 'Send message'}
            >
              {isLoading ? (
                <Square className="h-4 w-4" />
              ) : isSending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

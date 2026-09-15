'use client'
import { useState, useRef, useEffect } from 'react'
import { Send, Square } from 'lucide-react'
import { ModelSelector } from './model-selector'
import { ComposerTools } from './composer-tools'

interface ComposerProps {
  onSend: (content: string) => void
  isLoading?: boolean
  onStop?: () => void
  selectedModel?: string
  onModelChange?: (model: string) => void
}

export function Composer({ onSend, isLoading, onStop, selectedModel, onModelChange }: ComposerProps) {
  const [value, setValue] = useState('')
  const [isSending, setIsSending] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = async () => {
    if (!value.trim() || isLoading || isSending) return
    setIsSending(true)
    try {
      await onSend(value.trim())
    } finally {
      setIsSending(false)
    }
    setValue('')
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
        <div className="flex items-end gap-2 rounded-xl border bg-background p-2 shadow-sm">
          <ComposerTools />
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Send a message..."
            className="flex-1 resize-none border-0 bg-transparent px-2 py-2 text-sm focus:outline-none focus:ring-0 min-h-[40px] max-h-[200px]"
            rows={1}
            disabled={isLoading || isSending}
          />
          <button
            onClick={isLoading ? onStop : handleSubmit}
            className="mb-0.5 mr-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
            disabled={!value.trim() && !isLoading}
          >
            {isLoading ? <Square className="h-4 w-4" /> : <Send className="h-4 w-4" />}
          </button>
        </div>
        <div className="mt-2 flex justify-center">
          {selectedModel && onModelChange && (
            <ModelSelector value={selectedModel} onChange={onModelChange} models={[]} />
          )}
        </div>
      </div>
    </div>
  )
}

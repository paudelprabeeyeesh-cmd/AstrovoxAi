'use client'
import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Square, ImagePlus, Paperclip, X, Loader2 } from 'lucide-react'
import { ModelSelector } from './model-selector'
import { ComposerTools } from './composer-tools'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'

interface ComposerProps {
  onSend: (content: string, options?: { imageUrl?: string; files?: File[] }) => void
  isLoading?: boolean
  onStop?: () => void
  selectedModel?: string
  onModelChange?: (model: string) => void
}

const MAX_CHARS = 128000
const TOKEN_ESTIMATE_RATIO = 4

export function Composer({ onSend, isLoading, onStop, selectedModel, onModelChange }: ComposerProps) {
  const [value, setValue] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [isUploadingImage, setIsUploadingImage] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const charCount = value.length
  const estimatedTokens = Math.ceil(charCount / TOKEN_ESTIMATE_RATIO)
  const isOverLimit = charCount > MAX_CHARS

  const handleSubmit = async () => {
    if (!value.trim() || isLoading || isSending || isOverLimit) return

    setIsSending(true)
    try {
      await onSend(value.trim(), { imageUrl: imageUrl || undefined })
    } finally {
      setIsSending(false)
    }

    setValue('')
    setImageUrl(null)

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

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setIsUploadingImage(true)
    try {
      const formData = new FormData()
      formData.append('file', file)

      const res = await fetch('/api/files/upload', { method: 'POST', body: formData })
      if (!res.ok) throw new Error('Upload failed')

      const data = await res.json()
      const url = data.url
      setImageUrl(url)
    } catch (err) {
      console.error('Image upload failed:', err)
    } finally {
      setIsUploadingImage(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const clearImage = () => {
    setImageUrl(null)
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
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploadingImage || isLoading}
              className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground disabled:opacity-50"
              title="Upload image"
            >
              {isUploadingImage ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ImagePlus className="h-4 w-4" />
              )}
            </Button>

            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleImageUpload}
            />

            <ComposerTools disabled={isLoading || isSending} />
          </div>

          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={value}
              onChange={(e) => setValue(e.target.value.slice(0, MAX_CHARS))}
              onKeyDown={handleKeyDown}
              placeholder="Send a message..."
              className="w-full resize-none border-0 bg-transparent px-2 py-2 text-sm focus:outline-none focus:ring-0 min-h-[40px] max-h-[200px]"
              rows={1}
              disabled={isLoading || isSending}
            />

            {imageUrl && (
              <div className="absolute left-0 bottom-full mb-2">
                <div className="relative inline-flex items-center rounded-lg border border-border bg-muted p-1">
                  <img src={imageUrl} alt="Uploaded" className="h-12 w-12 rounded object-cover" />
                  <button
                    type="button"
                    onClick={clearImage}
                    className="absolute -top-1 -right-1 rounded-full bg-background p-0.5 hover:bg-muted"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="flex items-center gap-1">
            {isOverLimit && (
              <span className="text-xs text-red-500">Over limit</span>
            )}

            {!isOverLimit && charCount > 0 && (
              <span className="text-xs text-muted-foreground tabular-nums">
                {estimatedTokens} tokens
              </span>
            )}

            <Button
              onClick={isLoading ? onStop : handleSubmit}
              className="mb-0.5 mr-0.5 h-8 w-8 shrink-0 p-0"
              disabled={(!value.trim() && !imageUrl) || isOverLimit}
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

        <div className="mt-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            {selectedModel && onModelChange && (
              <ModelSelector value={selectedModel} onChange={onModelChange} models={[]} />
            )}
          </div>

          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className="tabular-nums">{charCount.toLocaleString()} / {MAX_CHARS.toLocaleString()} chars</span>
          </div>
        </div>
      </div>
    </div>
  )
}

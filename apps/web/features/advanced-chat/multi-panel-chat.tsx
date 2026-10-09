'use client'
import { useState, useCallback } from 'react'
import { Send, Square, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card } from '@/components/ui/card'
import { ModelOption } from '@/components/chat/types'

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  model?: string
  timestamp?: Date
}

interface MultiPanelChatProps {
  models: ModelOption[]
  selectedModels: string[]
  onSend: (content: string, model: string) => void
  isLoading?: boolean
}

export function MultiPanelChat({ models, selectedModels, onSend, isLoading }: MultiPanelChatProps) {
  const [value, setValue] = useState('')
  const [responses, setResponses] = useState<Record<string, Message[]>>({})

  const handleSubmit = useCallback(() => {
    if (!value.trim() || isLoading) return
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: value.trim(),
      timestamp: new Date(),
    }
    for (const model of selectedModels) {
      onSend(value.trim(), model)
    }
    setValue('')
  }, [value, isLoading, selectedModels, onSend])

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 grid gap-4" style={{ gridTemplateColumns: `repeat(${selectedModels.length}, 1fr)` }}>
        {selectedModels.map((modelId) => {
          const model = models.find((m) => m.id === modelId)
          const messages = responses[modelId] || []
          return (
            <Card key={modelId} className="flex flex-col overflow-hidden">
              <div className="border-b px-4 py-2 text-sm font-medium">{model?.name || modelId}</div>
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {messages.length === 0 && (
                  <p className="text-muted-foreground text-sm">Responses will appear here.</p>
                )}
                {messages.map((msg) => (
                  <div key={msg.id} className={msg.role === 'user' ? 'text-right' : 'text-left'}>
                    <div
                      className={
                        msg.role === 'user'
                          ? 'bg-primary text-primary-foreground inline-block rounded-lg px-3 py-2 text-sm'
                          : 'bg-muted inline-block rounded-lg px-3 py-2 text-sm'
                      }
                    >
                      {msg.content}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )
        })}
      </div>
      <div className="border-t p-4">
        <div className="flex gap-2">
          <Textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="Send a message to all selected models..."
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSubmit()
              }
            }}
            className="min-h-[60px]"
          />
          <Button onClick={handleSubmit} disabled={!value.trim() || isLoading}>
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </Button>
        </div>
      </div>
    </div>
  )
}

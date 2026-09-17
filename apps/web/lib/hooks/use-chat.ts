import { useCallback, useEffect, useRef, useState } from 'react'
import { useChatStore } from '@/lib/store/chat-store'
import { api } from '@/lib/api'
import { LIMITS } from '@/lib/constants'
import type { Message, ModelId } from '@/types'

export function useChat() {
  const {
    messages,
    conversations,
    activeId,
    isLoading,
    streamingMessageId,
    addMessage,
    updateLastMessage,
    setLoading,
    setStreamingMessageId,
  } = useChatStore()

  const [error, setError] = useState<Error | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const sendMessage = useCallback(
    async (content: string, modelId: ModelId) => {
      if (!activeId || !content.trim()) return

      setError(null)
      setLoading(true)
      abortControllerRef.current = new AbortController()

      const userMessage: Omit<Message, 'id' | 'timestamp'> = {
        role: 'user',
        content: content.trim(),
        conversationId: activeId,
      }
      addMessage(activeId, userMessage)

      try {
      const response = await api.post<{ message: Message }>('/chat', {
        conversationId: activeId,
        content: content.trim(),
        modelId: modelId as any,
      })

        if (response?.message) {
          addMessage(activeId, {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: response.message.content,
            conversationId: activeId,
            model: modelId as any,
            timestamp: Date.now(),
          } as any)
        }
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to send message'))
      } finally {
        setLoading(false)
        abortControllerRef.current = null
      }
    },
    [activeId, addMessage, setLoading]
  )

  const sendMessageStream = useCallback(
    async (content: string, modelId: ModelId) => {
      if (!activeId || !content.trim()) return

      setError(null)
      setLoading(true)
      abortControllerRef.current = new AbortController()

      const userMessage: Omit<Message, 'id' | 'timestamp'> = {
        role: 'user',
        content: content.trim(),
        conversationId: activeId,
      }
      addMessage(activeId, userMessage)

      const assistantMessageId = crypto.randomUUID()
      addMessage(activeId, {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        conversationId: activeId,
        model: modelId as any,
        timestamp: Date.now(),
      } as any)
      setStreamingMessageId(assistantMessageId)

      try {
        const response = await fetch('/api/chat/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ conversationId: activeId, content: content.trim(), modelId }),
          signal: abortControllerRef.current.signal,
        })

        if (!response.ok) throw new Error('Streaming failed')

        const reader = response.body?.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        if (!reader) throw new Error('No reader available')

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6)
              if (data === '[DONE]') break
              try {
                const parsed = JSON.parse(data)
                if (parsed.content) {
                  updateLastMessage(activeId, { content: parsed.content })
                }
              } catch {
                updateLastMessage(activeId, { content: line })
              }
            }
          }
        }
      } catch (err) {
        if ((err as Error).name !== 'AbortError') {
          setError(err instanceof Error ? err : new Error('Streaming failed'))
        }
      } finally {
        setLoading(false)
        setStreamingMessageId(null)
        abortControllerRef.current = null
      }
    },
    [activeId, addMessage, updateLastMessage, setLoading, setStreamingMessageId]
  )

  const stopStreaming = useCallback(() => {
    abortControllerRef.current?.abort()
    setLoading(false)
    setStreamingMessageId(null)
  }, [setLoading, setStreamingMessageId])

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort()
    }
  }, [])

  return {
    messages,
    conversations,
    activeId,
    isLoading,
    streamingMessageId,
    error,
    sendMessage,
    sendMessageStream,
    stopStreaming,
  }
}

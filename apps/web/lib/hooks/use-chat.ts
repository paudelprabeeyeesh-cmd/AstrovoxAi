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
    updateMessage,
    deleteMessage,
  } = useChatStore()

  const [error, setError] = useState<Error | null>(null)
  const [uploadedImage, setUploadedImage] = useState<string | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const sendMessage = useCallback(
    async (content: string, modelId: ModelId, imageUrl?: string) => {
      if (!activeId || !content.trim()) return

      setError(null)
      setLoading(true)
      abortControllerRef.current = new AbortController()

      const userMessage: Omit<Message, 'id' | 'timestamp'> = {
        role: 'user',
        content: content.trim(),
        conversationId: activeId,
      }

      if (imageUrl) {
        userMessage.content = `[Image uploaded]\n\n${content.trim()}`
      }

      addMessage(activeId, userMessage)

      try {
        const response = await api.post<{ message: Message }>('/chat', {
          conversationId: activeId,
          content: content.trim(),
          modelId: modelId as any,
          imageUrl,
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
        setUploadedImage(null)
      }
    },
    [activeId, addMessage, setLoading]
  )

  const sendMessageStream = useCallback(
    async (content: string, modelId: ModelId, imageUrl?: string) => {
      if (!activeId || !content.trim()) return

      setError(null)
      setLoading(true)
      abortControllerRef.current = new AbortController()

      const userMessage: Omit<Message, 'id' | 'timestamp'> = {
        role: 'user',
        content: content.trim(),
        conversationId: activeId,
      }

      if (imageUrl) {
        userMessage.content = `[Image uploaded]\n\n${content.trim()}`
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
        isStreaming: true,
      } as any)
      setStreamingMessageId(assistantMessageId)

      try {
        const response = await fetch('/api/chat/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            conversationId: activeId,
            content: content.trim(),
            modelId,
            imageUrl,
          }),
          signal: abortControllerRef.current.signal,
        })

        if (!response.ok) {
          const errorText = await response.text()
          throw new Error(`Streaming failed: ${response.status} ${errorText}`)
        }

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
              if (data === '[DONE]') {
                updateLastMessage(activeId, { isStreaming: false })
                break
              }

              try {
                const parsed = JSON.parse(data)
                if (parsed.content) {
                  updateLastMessage(activeId, {
                    content: parsed.content,
                    isStreaming: true,
                  })
                }

                if (parsed.error) {
                  setError(new Error(parsed.error))
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
          updateLastMessage(activeId, { isStreaming: false })
        }
      } finally {
        setLoading(false)
        setStreamingMessageId(null)
        abortControllerRef.current = null
        setUploadedImage(null)
      }
    },
    [activeId, addMessage, updateLastMessage, setLoading, setStreamingMessageId]
  )

  const stopStreaming = useCallback(() => {
    abortControllerRef.current?.abort()
    setLoading(false)
    setStreamingMessageId(null)

    if (activeId) {
      updateLastMessage(activeId, { isStreaming: false })
    }
  }, [setLoading, setStreamingMessageId, activeId, updateLastMessage])

  const regenerateMessage = useCallback(
    async (messageId: string) => {
      if (!activeId) return

      const messageIndex = messages.findIndex((m) => m.id === messageId)
      if (messageIndex < 0) return

      const previousMessage = messages[messageIndex - 1]
      if (!previousMessage || previousMessage.role !== 'user') return

      const messagesToDelete: string[] = []
      for (let i = messageIndex; i < messages.length; i++) {
        messagesToDelete.push(messages[i].id)
      }

      messagesToDelete.forEach((id) => deleteMessage(activeId, id))

      const modelId = (messages[messageIndex] as any)?.model || 'gpt-4'
      await sendMessageStream(previousMessage.content, modelId)
    },
    [activeId, messages, deleteMessage, sendMessageStream]
  )

  const editMessage = useCallback(
    async (messageId: string, newContent: string) => {
      if (!activeId) return

      updateMessage(activeId, messageId, { content: newContent })

      const messageIndex = messages.findIndex((m) => m.id === messageId)
      if (messageIndex < 0) return

      const messagesToDelete: string[] = []
      for (let i = messageIndex + 1; i < messages.length; i++) {
        messagesToDelete.push(messages[i].id)
      }

      messagesToDelete.forEach((id) => deleteMessage(activeId, id))

      const modelId = (messages[messageIndex] as any)?.model || 'gpt-4'
      await sendMessageStream(newContent, modelId)
    },
    [activeId, messages, updateMessage, deleteMessage, sendMessageStream]
  )

  const copyMessage = useCallback(async (content: string) => {
    await navigator.clipboard.writeText(content)
  }, [])

  const rateMessage = useCallback(
    (messageId: string, feedback: 'up' | 'down' | null) => {
      if (!activeId) return
      updateMessage(activeId, messageId, { feedback })
    },
    [activeId, updateMessage]
  )

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
    uploadedImage,
    sendMessage,
    sendMessageStream,
    stopStreaming,
    regenerateMessage,
    editMessage,
    copyMessage,
    rateMessage,
    setUploadedImage,
  }
}

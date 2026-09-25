import { useCallback, useEffect } from 'react'
import { useChatStore } from '@/lib/store/chat-store'
import { api } from '@/lib/api'
import type { Conversation } from '@/types'

export function useConversations() {
  const {
    conversations,
    activeId,
    setConversations,
    setActiveConversation,
    setMessages,
    clearMessages,
  } = useChatStore()

  const loadConversations = useCallback(async () => {
    try {
      const data = await api.get<any[]>('/conversations')
      setConversations(data as any)
    } catch (error) {
      console.error('Failed to load conversations:', error)
    }
  }, [setConversations])

  const createConversation = useCallback(
    async (title?: string) => {
      try {
        const conversation = await api.post<any>('/conversations', {
          title: title ?? 'New Conversation',
        })
        ;(setConversations as any)((prev: any[]) => [conversation, ...prev])
        setActiveConversation(conversation.id)
        setMessages(conversation.id, [])
        return conversation
      } catch (error) {
        console.error('Failed to create conversation:', error)
        return null
      }
    },
    [setConversations, setActiveConversation, setMessages]
  )

  const deleteConversation = useCallback(
    async (id: string) => {
      try {
        await api.delete(`/conversations/${id}`)
        ;(setConversations as any)((prev: any[]) => prev.filter((c: any) => c.id !== id))
        if (activeId === id) {
          setActiveConversation(null)
          clearMessages()
        }
      } catch (error) {
        console.error('Failed to delete conversation:', error)
      }
    },
    [activeId, setConversations, setActiveConversation, clearMessages]
  )

  const switchConversation = useCallback(
    (id: string) => {
      setActiveConversation(id)
    },
    [setActiveConversation]
  )

  useEffect(() => {
    loadConversations()
  }, [loadConversations])

  return {
    conversations,
    activeId,
    loadConversations,
    createConversation,
    deleteConversation,
    switchConversation,
  }
}

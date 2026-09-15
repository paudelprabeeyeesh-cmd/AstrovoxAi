import { useCallback, useEffect } from 'react'
import { useChatStore } from '@/lib/store/chat-store'
import { api } from '@/lib/api'

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
      const data = await api.get<Conversation[]>('/conversations')
      setConversations(data)
    } catch (error) {
      console.error('Failed to load conversations:', error)
    }
  }, [setConversations])

  const createConversation = useCallback(
    async (title?: string) => {
      try {
        const conversation = await api.post<Conversation>('/conversations', {
          title: title ?? 'New Conversation',
        })
        setConversations((prev) => [conversation, ...prev])
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
        setConversations((prev) => prev.filter((c) => c.id !== id))
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

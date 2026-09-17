import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import type { Message, Conversation } from '@/types'

interface ChatState {
  messages: Message[]
  conversations: Conversation[]
  activeId: string | null
  isLoading: boolean
  streamingMessageId: string | null
  addMessage: (conversationId: string, message: Omit<Message, 'id' | 'timestamp'>) => void
  updateLastMessage: (conversationId: string, updates: Partial<Message>) => void
  setActiveConversation: (id: string | null) => void
  setMessages: (conversationId: string, messages: Message[]) => void
  setConversations: (conversations: Conversation[]) => void
  setLoading: (loading: boolean) => void
  setStreamingMessageId: (id: string | null) => void
  clearMessages: () => void
}

export const useChatStore = create<ChatState>()(
  devtools(
    persist(
      (set, get) => ({
        messages: [],
        conversations: [],
        activeId: null,
        isLoading: false,
        streamingMessageId: null,

        addMessage: (conversationId, message) =>
          set((state) => ({
            messages: [
              ...state.messages,
              {
                ...message,
                id: crypto.randomUUID(),
                conversationId,
                timestamp: Date.now(),
              } as any as Message,
            ],
          })),

        updateLastMessage: (conversationId, updates) =>
          set((state) => ({
            messages: state.messages.map((msg, idx) =>
              idx === state.messages.length - 1 && msg.conversationId === conversationId
                ? { ...msg, ...updates }
                : msg
            ),
          })),

        setActiveConversation: (id) => set({ activeId: id }),
        setMessages: (conversationId, messages) =>
          set((state) => ({
            messages: state.messages.filter((m) => m.conversationId !== conversationId).concat(messages),
          })),
        setConversations: (conversations) => set({ conversations }),
        setLoading: (isLoading) => set({ isLoading }),
        setStreamingMessageId: (streamingMessageId) => set({ streamingMessageId }),
        clearMessages: () => set({ messages: [], streamingMessageId: null }),
      }),
      {
        name: 'chat-storage',
        partialize: (state) => ({
          conversations: state.conversations,
          activeId: state.activeId,
        }),
      }
    ),
    { name: 'ChatStore' }
  )
)

import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import type { Message, Conversation } from '@/types'

interface ChatState {
  messages: Message[]
  conversations: Conversation[]
  activeId: string | null
  isLoading: boolean
  streamingMessageId: string | null
  searchQuery: string
  addMessage: (conversationId: string, message: Omit<Message, 'id' | 'timestamp'>) => void
  updateLastMessage: (conversationId: string, updates: Partial<Message>) => void
  updateMessage: (conversationId: string, messageId: string, updates: Partial<Message>) => void
  deleteMessage: (conversationId: string, messageId: string) => void
  setActiveConversation: (id: string | null) => void
  setMessages: (conversationId: string, messages: Message[]) => void
  setConversations: (conversations: Conversation[]) => void
  setLoading: (loading: boolean) => void
  setStreamingMessageId: (id: string | null) => void
  setSearchQuery: (query: string) => void
  clearMessages: () => void
  pinConversation: (id: string) => void
  unpinConversation: (id: string) => void
  moveConversationToFolder: (id: string, folder: string) => void
  deleteConversation: (id: string) => void
  createFolder: (name: string) => void
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
        searchQuery: '',

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

        updateMessage: (conversationId, messageId, updates) =>
          set((state) => ({
            messages: state.messages.map((msg) =>
              msg.id === messageId && msg.conversationId === conversationId
                ? { ...msg, ...updates }
                : msg
            ),
          })),

        deleteMessage: (conversationId, messageId) =>
          set((state) => ({
            messages: state.messages.filter(
              (msg) => !(msg.id === messageId && msg.conversationId === conversationId)
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
        setSearchQuery: (searchQuery) => set({ searchQuery }),
        clearMessages: () => set({ messages: [], streamingMessageId: null }),

        pinConversation: (id) =>
          set((state) => ({
            conversations: state.conversations.map((c) =>
              c.id === id ? { ...c, pinned: true } : c
            ),
          })),

        unpinConversation: (id) =>
          set((state) => ({
            conversations: state.conversations.map((c) =>
              c.id === id ? { ...c, pinned: false } : c
            ),
          })),

        moveConversationToFolder: (id, folder) =>
          set((state) => ({
            conversations: state.conversations.map((c) =>
              c.id === id ? { ...c, folder } : c
            ),
          })),

        deleteConversation: (id) =>
          set((state) => ({
            conversations: state.conversations.filter((c) => c.id !== id),
          })),

        createFolder: (name) =>
          set((state) => ({
            conversations: [
              ...state.conversations,
              {
                id: crypto.randomUUID(),
                title: name,
                active: false,
                folder: name.toLowerCase().replace(/\s+/g, '-'),
              } as any as Conversation,
            ],
          })),
      }),
      {
        name: 'chat-storage',
        partialize: (state) => ({
          conversations: state.conversations,
          activeId: state.activeId,
          searchQuery: state.searchQuery,
        }),
      }
    ),
    { name: 'ChatStore' }
  )
)

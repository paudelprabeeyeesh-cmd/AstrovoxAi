import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import type { Message, Conversation } from '@/types'
import { api } from '@/lib/api'

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
  pinConversation: (id: string) => Promise<void>
  unpinConversation: (id: string) => Promise<void>
  moveConversationToFolder: (id: string, folder: string) => Promise<void>
  deleteConversation: (id: string) => Promise<void>
  archiveConversation: (id: string) => Promise<void>
  unarchiveConversation: (id: string) => Promise<void>
  createFolder: (name: string) => void
  createConversation: (title?: string, model?: string) => Promise<{ status: string; conversation: Conversation | null }>
  loadConversations: () => Promise<void>
  syncConversation: (conversation: Conversation) => void
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

        pinConversation: async (id) => {
          set((state) => ({
            conversations: state.conversations.map((c) =>
              c.id === id ? { ...c, pinned: true } : c
            ),
          }))
          try {
            await api.pinConversation(id)
          } catch {
            set((state) => ({
              conversations: state.conversations.map((c) =>
                c.id === id ? { ...c, pinned: false } : c
              ),
            }))
          }
        },

        unpinConversation: async (id) => {
          set((state) => ({
            conversations: state.conversations.map((c) =>
              c.id === id ? { ...c, pinned: false } : c
            ),
          }))
          try {
            await api.unpinConversation(id)
          } catch {
            set((state) => ({
              conversations: state.conversations.map((c) =>
                c.id === id ? { ...c, pinned: true } : c
              ),
            }))
          }
        },

        moveConversationToFolder: async (id, folder) => {
          set((state) => ({
            conversations: state.conversations.map((c) =>
              c.id === id ? { ...c, folder } : c
            ),
          }))
          try {
            await api.updateConversation(id, { folder })
          } catch {
            set((state) => ({
              conversations: state.conversations.map((c) =>
                c.id === id ? { ...c, folder: c.folder === folder ? null : c.folder } : c
              ),
            }))
          }
        },

  deleteConversation: async (id) => {
    set((state) => ({
      conversations: state.conversations.filter((c) => c.id !== id),
      messages: state.messages.filter((m) => m.conversationId !== id),
    }))
    try {
      await api.deleteConversation(id)
    } catch {
      set((state) => ({
        conversations: state.conversations,
        messages: state.messages,
      }))
    }
  },

  archiveConversation: async (id) => {
    set((state) => ({
      conversations: state.conversations.map((c) =>
        c.id === id ? { ...c, archived: true } : c
      ),
    }))
    try {
      await api.archiveConversation(id)
    } catch {
      set((state) => ({
        conversations: state.conversations.map((c) =>
          c.id === id ? { ...c, archived: false } : c
        ),
      }))
    }
  },

  unarchiveConversation: async (id) => {
    set((state) => ({
      conversations: state.conversations.map((c) =>
        c.id === id ? { ...c, archived: false } : c
      ),
    }))
    try {
      await api.unarchiveConversation(id)
    } catch {
      set((state) => ({
        conversations: state.conversations.map((c) =>
          c.id === id ? { ...c, archived: true } : c
        ),
      }))
    }
  },

  createConversation: async (title, model) => {
    try {
      const response = await api.createConversation(title, model)
      const conversation = (response as any).conversation
      if (conversation) {
        set((state) => ({
          conversations: [conversation, ...state.conversations],
          activeId: conversation.id,
        }))
        return { status: 'success', conversation }
      }
    } catch {
      const newId = crypto.randomUUID()
      const newConv = {
        id: newId,
        title: title || 'New Chat',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        model: model || 'gpt-4',
        pinned: false,
        folder: null,
        archived: false,
        messageCount: 0,
        preview: '',
      } as any as Conversation
      set((state) => ({
        conversations: [newConv, ...state.conversations],
        activeId: newId,
      }))
      return { status: 'success', conversation: newConv }
    }
    return { status: 'error', conversation: null as any }
  },

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

        loadConversations: async () => {
          set({ isLoading: true })
          try {
            const response = await api.getConversations()
            const conversations = (response as any).conversations || []
            set({ conversations })
          } catch {
            // keep local state on failure
          } finally {
            set({ isLoading: false })
          }
        },

        syncConversation: (conversation) =>
          set((state) => {
            const exists = state.conversations.some((c) => c.id === conversation.id)
            if (exists) {
              return {
                conversations: state.conversations.map((c) =>
                  c.id === conversation.id ? { ...c, ...conversation } : c
                ),
              }
            }
            return { conversations: [conversation, ...state.conversations] }
          }),
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

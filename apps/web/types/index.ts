export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  conversationId: string
  model?: string
  timestamp?: string | Date
  isStreaming?: boolean
  citations?: Citation[]
  feedback?: 'up' | 'down' | null
  tools?: ToolCall[]
}

export interface Citation {
  id: string
  title: string
  url?: string
  snippet: string
  verified?: boolean
}

export interface ToolCall {
  id: string
  name: string
  arguments: Record<string, unknown>
  result?: unknown
  status: 'pending' | 'running' | 'completed' | 'failed'
}

export interface Conversation {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  model?: string
  messageCount?: number
  preview?: string
  pinned?: boolean
  folder?: string
}

export interface ModelOption {
  id: string
  name: string
  provider: string
  contextWindow?: number
  capabilities?: string[]
}

export interface Suggestion {
  id: string
  title: string
  description?: string
  prompt: string
}

export interface DocumentItem {
  id: string
  filename: string
  status: string
  chunks: number
  createdAt: string
}

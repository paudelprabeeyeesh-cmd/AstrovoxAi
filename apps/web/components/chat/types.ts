export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  createdAt: Date
  isStreaming?: boolean
}

export interface ModelOption {
  id: string
  name: string
  provider: string
}

export interface Suggestion {
  id: string
  title: string
  description?: string
  prompt: string
}

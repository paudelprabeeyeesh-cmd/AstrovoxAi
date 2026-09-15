export const MODELS = {
  'gpt-4o': { id: 'gpt-4o', name: 'GPT-4o', provider: 'OpenAI' },
  'claude-3.5-sonnet': { id: 'claude-3.5-sonnet', name: 'Claude 3.5 Sonnet', provider: 'Anthropic' },
  'gemini-2.0-flash': { id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash', provider: 'Google' },
} as const

export type ModelId = keyof typeof MODELS

export const LIMITS = {
  maxMessagesPerConversation: 100,
  maxConversations: 50,
  maxMessageLength: 32000,
  streamingChunkSize: 1024,
} as const

export const ROUTES = {
  HOME: '/',
  CHAT: '/chat',
  SETTINGS: '/settings',
  API_CHAT: '/api/chat',
  API_CONVERSATIONS: '/api/conversations',
} as const

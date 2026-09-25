export interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp?: string
}

export interface Conversation {
  id: string
  title: string
  messages: Message[]
  model: string
  createdAt?: string
}

export interface SendMessageOptions {
  conversationId: string
  message: string
  model?: string
  stream?: boolean
}

export interface CreateConversationOptions {
  title?: string
  model?: string
}

export class AstrovoxClient {
  private apiKey: string
  private baseUrl: string
  private headers: Record<string, string>

  constructor(apiKey: string, baseUrl: string = 'https://api.astrovox.ai/v1') {
    this.apiKey = apiKey
    this.baseUrl = baseUrl.replace(/\/$/, '')
    this.headers = {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json'
    }
  }

  async sendMessage(options: SendMessageOptions): Promise<{ ai_message: Message }> {
    const response = await fetch(`${this.baseUrl}/chat/message`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({
        conversation_id: options.conversationId,
        message: options.message,
        model: options.model || 'gpt-4'
      })
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    return response.json()
  }

  async *streamMessage(options: SendMessageOptions): AsyncGenerator<string, void, unknown> {
    const response = await fetch(`${this.baseUrl}/chat/stream`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({
        conversation_id: options.conversationId,
        message: options.message,
        model: options.model || 'gpt-4'
      })
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const reader = response.body?.getReader()
    if (!reader) throw new Error('No response body')
    const decoder = new TextDecoder()
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      yield decoder.decode(value)
    }
  }

  async createConversation(options: CreateConversationOptions = {}): Promise<Conversation> {
    const response = await fetch(`${this.baseUrl}/conversations`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({
        title: options.title || 'New Conversation',
        model: options.model || 'gpt-4'
      })
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    return {
      id: data.id,
      title: data.title,
      messages: [],
      model: data.model,
      createdAt: data.created_at
    }
  }

  async listConversations(): Promise<Conversation[]> {
    const response = await fetch(`${this.baseUrl}/conversations`, { headers: this.headers })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    return data.map((c: any) => ({
      id: c.id,
      title: c.title,
      messages: [],
      model: c.model || 'gpt-4',
      createdAt: c.created_at
    }))
  }

  async deleteConversation(conversationId: string): Promise<boolean> {
    const response = await fetch(`${this.baseUrl}/conversations/${conversationId}`, {
      method: 'DELETE',
      headers: this.headers
    })
    return response.status === 204
  }

  async healthCheck(): Promise<Record<string, any>> {
    const response = await fetch(`${this.baseUrl}/health`)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    return response.json()
  }
}

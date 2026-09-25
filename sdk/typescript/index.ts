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

export interface WebhookConfig {
  url: string
  secret?: string
  events: string[]
  active?: boolean
}

export interface RetryPolicy {
  maxRetries?: number
  backoffFactor?: number
  retryableStatuses?: number[]
}

export interface ExportOptions {
  format?: 'json' | 'markdown' | 'csv'
}

export class AstrovoxClient {
  private apiKey: string
  private baseUrl: string
  private headers: Record<string, string>
  private retryPolicy: RetryPolicy

  constructor(apiKey: string, baseUrl: string = 'https://api.astrovox.ai/v1', retryPolicy: RetryPolicy = {}) {
    this.apiKey = apiKey
    this.baseUrl = baseUrl.replace(/\/$/, '')
    this.headers = {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json'
    }
    this.retryPolicy = {
      maxRetries: retryPolicy.maxRetries ?? 3,
      backoffFactor: retryPolicy.backoffFactor ?? 1.0,
      retryableStatuses: retryPolicy.retryableStatuses ?? [429, 500, 502, 503, 504]
    }
  }

  private async request(method: string, path: string, options: RequestInit = {}): Promise<Response> {
    const url = `${this.baseUrl}${path}`
    const config: RequestInit = {
      ...options,
      method,
      headers: { ...this.headers, ...(options.headers ?? {}) }
    }
    let response = await fetch(url, config)
    const retryable = this.retryPolicy.retryableStatuses ?? []
    if (retryable.includes(response.status) && (this.retryPolicy.maxRetries ?? 3) > 0) {
      response = await this.retry(method, path, response, config)
    }
    if (!response.ok) {
      const text = await response.text().catch(() => 'Unknown error')
      throw new Error(`HTTP ${response.status}: ${text}`)
    }
    return response
  }

  private async retry(method: string, path: string, initial: Response, config: RequestInit): Promise<Response> {
    let response = initial
    const maxRetries = this.retryPolicy.maxRetries ?? 3
    const backoffFactor = this.retryPolicy.backoffFactor ?? 1.0
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      const wait = backoffFactor * 2 ** attempt
      await new Promise(resolve => setTimeout(resolve, wait * 1000))
      response = await fetch(`${this.baseUrl}${path}`, config)
      if (!(this.retryPolicy.retryableStatuses ?? []).includes(response.status)) {
        break
      }
    }
    return response
  }

  async sendMessage(options: SendMessageOptions): Promise<{ ai_message: Message }> {
    const response = await this.request('POST', '/chat/message', {
      body: JSON.stringify({
        conversation_id: options.conversationId,
        message: options.message,
        model: options.model || 'gpt-4'
      })
    })
    return response.json()
  }

  async *streamMessage(options: SendMessageOptions): AsyncGenerator<string, void, unknown> {
    const response = await this.request('POST', '/chat/stream', {
      body: JSON.stringify({
        conversation_id: options.conversationId,
        message: options.message,
        model: options.model || 'gpt-4'
      })
    })
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
    const response = await this.request('POST', '/conversations', {
      body: JSON.stringify({
        title: options.title || 'New Conversation',
        model: options.model || 'gpt-4'
      })
    })
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
    const response = await this.request('GET', '/conversations')
    const data = await response.json()
    return data.map((c: any) => ({
      id: c.id,
      title: c.title,
      messages: [],
      model: c.model || 'gpt-4',
      createdAt: c.created_at
    }))
  }

  async getConversation(conversationId: string): Promise<Conversation> {
    const response = await this.request('GET', `/conversations/${conversationId}`)
    const data = await response.json()
    return {
      id: data.id,
      title: data.title,
      messages: data.messages || [],
      model: data.model || 'gpt-4',
      createdAt: data.created_at
    }
  }

  async deleteConversation(conversationId: string): Promise<boolean> {
    const response = await this.request('DELETE', `/conversations/${conversationId}`)
    return response.status === 204
  }

  async createWebhook(config: WebhookConfig): Promise<any> {
    const response = await this.request('POST', '/webhooks', {
      body: JSON.stringify({
        url: config.url,
        secret: config.secret,
        events: config.events,
        active: config.active ?? true
      })
    })
    return response.json()
  }

  async listWebhooks(): Promise<any[]> {
    const response = await this.request('GET', '/webhooks')
    return response.json()
  }

  async deleteWebhook(webhookId: string): Promise<boolean> {
    const response = await this.request('DELETE', `/webhooks/${webhookId}`)
    return response.status === 204
  }

  async exportConversation(conversationId: string, format: ExportOptions['format'] = 'json'): Promise<Blob> {
    const response = await this.request('GET', `/conversations/${conversationId}/export?format=${format}`)
    return response.blob()
  }

  async importConversation(data: Blob, format: ExportOptions['format'] = 'json'): Promise<Conversation> {
    const response = await this.request('POST', '/conversations/import', {
      body: data,
      headers: { 'Content-Type': `application/${format}` }
    })
    return response.json()
  }

  async healthCheck(): Promise<Record<string, any>> {
    const response = await this.request('GET', '/health')
    return response.json()
  }

  async authenticateWithProvider(provider: string, token: string): Promise<any> {
    const response = await this.request('POST', '/auth/providers', {
      body: JSON.stringify({ provider, token })
    })
    return response.json()
  }

  async registerPlugin(manifest: Record<string, any>): Promise<any> {
    const response = await this.request('POST', '/plugins/register', {
      body: JSON.stringify(manifest)
    })
    return response.json()
  }
}

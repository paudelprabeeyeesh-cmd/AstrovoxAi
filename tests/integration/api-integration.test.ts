import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AstrovoxClient } from '../../sdk/typescript'

describe('API Integration Tests', () => {
  let client: AstrovoxClient

  beforeEach(() => {
    client = new AstrovoxClient({ apiKey: 'test-api-key' })
    vi.clearAllMocks()
  })

  it('creates a conversation via API', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        id: 'conv-1',
        title: 'Test Conversation',
        model: 'gpt-4',
        created_at: '2025-01-15T10:00:00Z'
      })
    })

    const result = await client.createConversation({ title: 'Test Conversation', model: 'gpt-4' })
    expect(result.id).toBe('conv-1')
    expect(result.title).toBe('Test Conversation')
    expect(result.model).toBe('gpt-4')
  })

  it('lists conversations', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([
        { id: 'conv-1', title: 'Chat 1', model: 'gpt-4', created_at: '2025-01-15T10:00:00Z' },
        { id: 'conv-2', title: 'Chat 2', model: 'gpt-4', created_at: '2025-01-15T10:00:00Z' }
      ])
    })

    const result = await client.listConversations()
    expect(Array.isArray(result)).toBe(true)
    expect(result).toHaveLength(2)
  })

  it('sends a message', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        ai_message: {
          id: 'msg-1',
          role: 'assistant',
          content: 'Hello! How can I help?',
          created_at: '2025-01-15T10:00:00Z'
        }
      })
    })

    const result = await client.sendMessage({ conversationId: 'conv-1', message: 'Hello' })
    expect(result.ai_message.content).toBe('Hello! How can I help?')
  })

  it('deletes a conversation', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 204
    })

    const result = await client.deleteConversation('conv-1')
    expect(result).toBe(true)
  })

  it('performs health check', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: 'healthy', timestamp: '2025-01-15T10:00:00Z' })
    })

    const result = await client.healthCheck()
    expect(result.status).toBe('healthy')
  })
})

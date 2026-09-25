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

  it('handles network failure gracefully', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Network connection lost'))

    await expect(client.sendMessage({ conversationId: '1', message: 'Hello' })).rejects.toThrow('Network connection lost')
  })

  it('handles 404 response', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      text: () => Promise.resolve('Not found')
    })

    await expect(client.sendMessage({ conversationId: '1', message: 'Hello' })).rejects.toThrow('HTTP 404')
  })

  it('handles 500 response', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      text: () => Promise.resolve('Server error')
    })

    await expect(client.sendMessage({ conversationId: '1', message: 'Hello' })).rejects.toThrow('HTTP 500')
  })

  it('retries on 503 and succeeds', async () => {
    let calls = 0
    global.fetch = vi.fn().mockImplementation(() => {
      calls++
      if (calls < 3) {
        return Promise.resolve({ ok: false, status: 503, statusText: 'Service Unavailable' })
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ ai_message: { id: '1', role: 'assistant', content: 'ok' } })
      })
    })

    const result = await client.sendMessage({ conversationId: '1', message: 'Hello' })
    expect(result.ai_message.content).toBe('ok')
    expect(calls).toBeGreaterThanOrEqual(3)
  })

  it('handles empty message body', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ ai_message: { id: '1', role: 'assistant', content: 'Hello' } }),
      status: 200
    })

    await client.sendMessage({ conversationId: '1', message: '' })
    const body = JSON.parse((fetch as any).mock.calls[0][1].body)
    expect(body.message).toBe('')
  })

  it('handles very long message', async () => {
    const longMessage = 'A'.repeat(100000)
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ ai_message: { id: '1', role: 'assistant', content: 'Received' } }),
      status: 200
    })

    await client.sendMessage({ conversationId: '1', message: longMessage })
    const body = JSON.parse((fetch as any).mock.calls[0][1].body)
    expect(body.message).toBe(longMessage)
  })

  it('handles special characters in message', async () => {
    const special = 'Hello 世界 🌍 <script>alert("xss")</script>'
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ ai_message: { id: '1', role: 'assistant', content: 'ok' } }),
      status: 200
    })

    await client.sendMessage({ conversationId: '1', message: special })
    const body = JSON.parse((fetch as any).mock.calls[0][1].body)
    expect(body.message).toBe(special)
  })

  it('handles unicode in conversation title', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: '1', title: '日本語', model: 'gpt-4', created_at: '2025-01-01T00:00:00Z' }),
      status: 200
    })

    const result = await client.createConversation({ title: '日本語' })
    expect(result.title).toBe('日本語')
  })

  it('getConversation returns conversation with messages', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: '1', title: 'Test', messages: [], model: 'gpt-4', created_at: '2025-01-01T00:00:00Z' }),
      status: 200
    })

    const result = await client.getConversation('1')
    expect(result.id).toBe('1')
    expect(result.messages).toEqual([])
  })

  it('deleteConversation returns false for non-204', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found'
    })

    const result = await client.deleteConversation('999')
    expect(result).toBe(false)
  })
})
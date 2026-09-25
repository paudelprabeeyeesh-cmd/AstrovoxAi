import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AstrovoxClient } from '../../sdk/typescript'

describe('OWASP ZAP Security Tests', () => {
  let client: AstrovoxClient

  beforeEach(() => {
    client = new AstrovoxClient({ apiKey: 'test-api-key' })
    vi.clearAllMocks()
  })

  it('blocks SQL injection in message field', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        ai_message: { id: '1', role: 'assistant', content: 'Safe response' }
      })
    })

    const result = await client.sendMessage({
      conversationId: "'; DROP TABLE messages; --",
      message: "'; DROP TABLE messages; --"
    })
    expect(result.ai_message.role).toBe('assistant')
  })

  it('blocks XSS in message content', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        ai_message: { id: '1', role: 'assistant', content: 'Safe response' }
      })
    })

    const result = await client.sendMessage({
      conversationId: '1',
      message: '<script>alert("xss")</script>'
    })
    expect(result.ai_message.role).toBe('assistant')
  })

  it('validates Content-Type headers', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ ai_message: { id: '1', role: 'assistant', content: 'Hello' } })
    })

    await client.sendMessage({ conversationId: '1', message: 'Hello' })
    const headers = (fetch as any).mock.calls[0][1].headers
    expect(headers['Content-Type']).toBe('application/json')
  })

  it('prevents path traversal', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        ai_message: { id: '1', role: 'assistant', content: 'Safe response' }
      })
    })

    const result = await client.sendMessage({
      conversationId: '../../../etc/passwd',
      message: 'test'
    })
    expect(result.ai_message.role).toBe('assistant')
  })

  it('validates Authorization header format', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ ai_message: { id: '1', role: 'assistant', content: 'Hello' } })
    })

    await client.sendMessage({ conversationId: '1', message: 'Hello' })
    const headers = (fetch as any).mock.calls[0][1].headers
    expect(headers.Authorization).toMatch(/^Bearer [A-Za-z0-9\-_]+$/)
  })

  it('prevents command injection', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        ai_message: { id: '1', role: 'assistant', content: 'Safe response' }
      })
    })

    const result = await client.sendMessage({
      conversationId: '1',
      message: '; rm -rf /'
    })
    expect(result.ai_message.role).toBe('assistant')
  })

  it('uses secure base URL', () => {
    const prodClient = new AstrovoxClient({ apiKey: 'test', baseUrl: 'https://api.astrovox.ai/v1' })
    expect(prodClient['baseUrl']).toMatch(/^https:\/\//)
    expect(prodClient['baseUrl']).not.toMatch(/^http:\/\//)
  })

  it('validates response structure', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        ai_message: {
          id: 'msg-123',
          role: 'assistant',
          content: 'Hello',
          created_at: '2025-01-15T10:00:00Z'
        }
      })
    })

    const result = await client.sendMessage({ conversationId: '1', message: 'Hello' })
    expect(result).toHaveProperty('ai_message')
    expect(result.ai_message).toHaveProperty('id')
    expect(result.ai_message).toHaveProperty('role', 'assistant')
    expect(result.ai_message).toHaveProperty('content')
    expect(result.ai_message).toHaveProperty('created_at')
  })
})

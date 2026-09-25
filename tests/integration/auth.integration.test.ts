import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AstrovoxClient } from '../../sdk/typescript'

describe('Auth Integration Tests', () => {
  let client: AstrovoxClient

  beforeEach(() => {
    client = new AstrovoxClient({ apiKey: 'test-api-key' })
    vi.clearAllMocks()
  })

  it('rejects requests without API key', async () => {
    const unauthenticatedClient = new AstrovoxClient({ apiKey: '' })
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      statusText: 'Unauthorized'
    })

    await expect(unauthenticatedClient.sendMessage({ conversationId: '1', message: 'Hello' })).rejects.toThrow()
  })

  it('rejects requests with invalid API key', async () => {
    const invalidClient = new AstrovoxClient({ apiKey: 'invalid-key' })
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      statusText: 'Unauthorized'
    })

    await expect(invalidClient.sendMessage({ conversationId: '1', message: 'Hello' })).rejects.toThrow()
  })

  it('handles expired tokens', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      statusText: 'Token expired'
    })

    await expect(client.sendMessage({ conversationId: '1', message: 'Hello' })).rejects.toThrow()
  })

  it('handles rate limit responses', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 429,
      statusText: 'Too Many Requests',
      headers: new Map([['Retry-After', '60']])
    })

    await expect(client.sendMessage({ conversationId: '1', message: 'Hello' })).rejects.toThrow()
  })

  it('uses HTTPS in production', () => {
    const prodClient = new AstrovoxClient({ apiKey: 'test', baseUrl: 'https://api.astrovox.ai/v1' })
    expect(prodClient['baseUrl']).toMatch(/^https:\/\//)
  })
})

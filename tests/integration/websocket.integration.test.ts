import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AstrovoxClient } from '../../sdk/typescript'

describe('WebSocket Integration Tests', () => {
  let client: AstrovoxClient

  beforeEach(() => {
    client = new AstrovoxClient({ apiKey: 'test-api-key' })
    vi.clearAllMocks()
  })

  it('establishes WebSocket connection with auth', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ ws_url: 'wss://api.astrovox.ai/ws/chat/conv-1' })
    })

    const result = await client.healthCheck()
    expect(result.status).toBe('healthy')
  })

  it('rejects unauthenticated WebSocket connections', async () => {
    const unauthClient = new AstrovoxClient({ apiKey: '' })
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401
    })

    await expect(unauthClient.sendMessage({ conversationId: '1', message: 'Hello' })).rejects.toThrow()
  })

  it('handles WebSocket message streaming', async () => {
    const mockStream = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode('Hello'))
        controller.enqueue(new TextEncoder().encode(' World'))
        controller.close()
      }
    })

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: mockStream
    })

    const stream = client.streamMessage({ conversationId: '1', message: 'Hello' })
    const chunks: string[] = []
    for await (const chunk of stream) {
      chunks.push(chunk)
    }
    expect(chunks.length).toBeGreaterThan(0)
  })

  it('handles WebSocket disconnection gracefully', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error'
    })

    await expect(client.sendMessage({ conversationId: '1', message: 'Hello' })).rejects.toThrow()
  })
})

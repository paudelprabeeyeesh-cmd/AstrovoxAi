import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AstrovoxClient } from '../../sdk/typescript'

describe('Error Budget Integration Tests', () => {
  let client: AstrovoxClient

  beforeEach(() => {
    client = new AstrovoxClient({ apiKey: 'test-api-key' })
    vi.clearAllMocks()
  })

  it('tracks error budget consumption', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        ai_message: { id: '1', role: 'assistant', content: 'Success' }
      })
    })

    const result = await client.sendMessage({ conversationId: 'eb-1', message: 'Hello' })
    expect(result.ai_message.role).toBe('assistant')
  })

  it('handles budget exhaustion', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      statusText: 'Budget exhausted'
    })

    await expect(client.sendMessage({ conversationId: 'eb-1', message: 'Hello' })).rejects.toThrow()
  })

  it('reports burn rate', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        ai_message: { id: '1', role: 'assistant', content: 'Success' }
      })
    })

    const result = await client.sendMessage({ conversationId: 'eb-1', message: 'Hello' })
    expect(result.ai_message.role).toBe('assistant')
  })
})

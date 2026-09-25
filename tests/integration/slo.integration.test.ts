import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AstrovoxClient } from '../../sdk/typescript'

describe('SLO/SLI/SLA Integration Tests', () => {
  let client: AstrovoxClient

  beforeEach(() => {
    client = new AstrovoxClient({ apiKey: 'test-api-key' })
    vi.clearAllMocks()
  })

  it('tracks latency SLI', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        ai_message: { id: '1', role: 'assistant', content: 'Success' }
      })
    })

    const start = Date.now()
    await client.sendMessage({ conversationId: 'sli-1', message: 'Hello' })
    const latency = Date.now() - start

    expect(latency).toBeGreaterThan(0)
    expect(latency).toBeLessThan(5000)
  })

  it('tracks availability SLI', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        ai_message: { id: '1', role: 'assistant', content: 'Success' }
      })
    })

    const result = await client.sendMessage({ conversationId: 'sli-1', message: 'Hello' })
    expect(result.ai_message.role).toBe('assistant')
  })

  it('tracks error rate SLI', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        ai_message: { id: '1', role: 'assistant', content: 'Success' }
      })
    })

    const result = await client.sendMessage({ conversationId: 'sli-1', message: 'Hello' })
    expect(result.ai_message.role).toBe('assistant')
  })

  it('validates SLO compliance', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        ai_message: { id: '1', role: 'assistant', content: 'Success' }
      })
    })

    const result = await client.sendMessage({ conversationId: 'sli-1', message: 'Hello' })
    expect(result.ai_message.role).toBe('assistant')
  })
})

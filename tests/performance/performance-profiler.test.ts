import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AstrovoxClient } from '../../sdk/typescript'

describe('Performance Profiler Tests', () => {
  let client: AstrovoxClient

  beforeEach(() => {
    client = new AstrovoxClient({ apiKey: 'test-api-key' })
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('measures message send latency', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ ai_message: { id: '1', role: 'assistant', content: 'Hello' } })
    })

    const start = Date.now()
    await client.sendMessage({ conversationId: 'perf-1', message: 'Hello' })
    const duration = Date.now() - start

    expect(duration).toBeLessThan(5000)
  })

  it('measures streaming latency', async () => {
    const mockStream = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode('Hello'))
        controller.close()
      }
    })

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: mockStream
    })

    const start = Date.now()
    const stream = client.streamMessage({ conversationId: 'perf-1', message: 'Hello' })
    const chunks: string[] = []
    for await (const chunk of stream) {
      chunks.push(chunk)
    }
    const duration = Date.now() - start

    expect(chunks.length).toBeGreaterThan(0)
    expect(duration).toBeLessThan(5000)
  })

  it('handles concurrent requests', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ ai_message: { id: '1', role: 'assistant', content: 'Hello' } })
    })

    const promises = Array.from({ length: 10 }, (_, i) =>
      client.sendMessage({ conversationId: `perf-${i}`, message: 'Hello' })
    )

    const results = await Promise.all(promises)
    expect(results).toHaveLength(10)
    expect(results.every(r => r.ai_message.content === 'Hello')).toBe(true)
  })

  it('measures health check latency', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: 'healthy' })
    })

    const start = Date.now()
    await client.healthCheck()
    const duration = Date.now() - start

    expect(duration).toBeLessThan(1000)
  })

  it('profiles memory usage during batch operations', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ ai_message: { id: '1', role: 'assistant', content: 'Hello' } })
    })

    const startMemory = process.memoryUsage?.()?.heapUsed || 0

    const promises = Array.from({ length: 100 }, (_, i) =>
      client.sendMessage({ conversationId: `perf-batch-${i}`, message: 'Hello' })
    )

    await Promise.all(promises)

    const endMemory = process.memoryUsage?.()?.heapUsed || 0
    const memoryIncrease = endMemory - startMemory

    expect(memoryIncrease).toBeLessThan(50 * 1024 * 1024)
  })

  it('measures API response time distribution', async () => {
    const latencies: number[] = []
    global.fetch = vi.fn().mockImplementation(() => {
      const start = Date.now()
      return new Promise((resolve) => {
        setTimeout(() => {
          latencies.push(Date.now() - start)
          resolve({
            ok: true,
            json: () => Promise.resolve({ ai_message: { id: '1', role: 'assistant', content: 'Hello' } })
          })
        }, Math.random() * 100)
      })
    })

    const promises = Array.from({ length: 20 }, () =>
      client.sendMessage({ conversationId: 'perf-dist', message: 'Hello' })
    )

    await Promise.all(promises)

    const sorted = latencies.sort((a, b) => a - b)
    const p95 = sorted[Math.floor(sorted.length * 0.95)]
    const p99 = sorted[Math.floor(sorted.length * 0.99)]

    expect(p95).toBeLessThan(200)
    expect(p99).toBeLessThan(500)
  })
})

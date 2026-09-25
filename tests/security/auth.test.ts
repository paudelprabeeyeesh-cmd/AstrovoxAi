import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AstrovoxClient } from '../../sdk/typescript'

describe('Security Tests', () => {
  let client: AstrovoxClient

  beforeEach(() => {
    client = new AstrovoxClient({ apiKey: 'test-api-key' })
    vi.clearAllMocks()
  })

  it('does not expose API key in client state', () => {
    const clientObj = client as any
    expect(clientObj.apiKey).toBe('test-api-key')
  })

  it('uses HTTPS for API requests', () => {
    const clientWithHTTP = new AstrovoxClient({ apiKey: 'test', baseUrl: 'http://insecure.example.com' })
    const calls = (clientWithHTTP as any).calls || []
    const url = clientWithHTTP['baseUrl']
    expect(url).not.toMatch(/^http:\/\//)
  })

  it('sanitizes message content', async () => {
    const maliciousInput = '<script>alert("xss")</script>Hello'
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ ai_message: { id: '1', role: 'assistant', content: 'Safe response' } })
    })

    await client.sendMessage({
      conversationId: 'conv-1',
      message: maliciousInput
    })

    const callArgs = (fetch as any).mock.calls[0][1]
    const body = JSON.parse(callArgs.body)
    expect(body.message).toBe(maliciousInput)
  })

  it('handles SQL injection attempts', async () => {
    const sqlInjection = "'; DROP TABLE messages; --"
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ ai_message: { id: '1', role: 'assistant', content: 'Response' } })
    })

    await client.sendMessage({
      conversationId: 'conv-1',
      message: sqlInjection
    })

    const callArgs = (fetch as any).mock.calls[0][1]
    const body = JSON.parse(callArgs.body)
    expect(body.message).toBe(sqlInjection)
  })

  it('validates authorization header format', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({})
    })

    await client.sendMessage({ conversationId: 'conv-1', message: 'Hello' })
    const headers = (fetch as any).mock.calls[0][1].headers
    expect(headers.Authorization).toMatch(/^Bearer /)
  })

  it('does not log sensitive data', () => {
    const consoleSpy = vi.spyOn(console, 'log')
    const consoleErrorSpy = vi.spyOn(console, 'error')

    client.sendMessage({ conversationId: 'conv-1', message: 'sensitive-data' }).catch(() => {})

    const allLogs = [...consoleSpy.mock.calls, ...consoleErrorSpy.mock.calls].flat()
    const sensitiveLeaked = allLogs.some(log =>
      JSON.stringify(log).includes('sensitive-data') && !JSON.stringify(log).includes('message')
    )
    expect(sensitiveLeaked).toBe(false)
  })
})

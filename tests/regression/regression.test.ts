import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AstrovoxClient } from '../../sdk/typescript'

describe('Regression Tests', () => {
  let client: AstrovoxClient

  beforeEach(() => {
    client = new AstrovoxClient({ apiKey: 'test-api-key' })
    vi.clearAllMocks()
  })

  it('sendMessage preserves backward-compatible response shape', async () => {
    const mockResponse = {
      ai_message: {
        id: 'msg-123',
        role: 'assistant',
        content: 'Hello!',
        created_at: '2025-01-15T10:00:00Z'
      }
    }
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
      status: 200
    })

    const result = await client.sendMessage({
      conversationId: 'conv-123',
      message: 'Hello',
      model: 'gpt-4'
    })

    expect(result).toHaveProperty('ai_message')
    expect(result.ai_message).toMatchObject({
      id: expect.any(String),
      role: 'assistant',
      content: expect.any(String),
      created_at: expect.any(String)
    })
  })

  it('createConversation preserves backward-compatible response shape', async () => {
    const mockResponse = {
      id: 'conv-456',
      title: 'New Conversation',
      model: 'gpt-4',
      created_at: '2025-01-15T10:00:00Z'
    }
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
      status: 200
    })

    const result = await client.createConversation({ title: 'New Conversation', model: 'gpt-4' })

    expect(result).toMatchObject({
      id: expect.any(String),
      title: 'New Conversation',
      model: 'gpt-4',
      messages: expect.any(Array),
      createdAt: expect.any(String)
    })
  })

  it('listConversations preserves backward-compatible response shape', async () => {
    const mockResponse = [
      { id: 'conv-1', title: 'Chat 1', model: 'gpt-4', created_at: '2025-01-15T10:00:00Z' },
      { id: 'conv-2', title: 'Chat 2', model: 'gpt-4', created_at: '2025-01-15T10:00:00Z' }
    ]
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
      status: 200
    })

    const result = await client.listConversations()

    expect(Array.isArray(result)).toBe(true)
    expect(result).toHaveLength(2)
    expect(result[0]).toMatchObject({
      id: expect.any(String),
      title: expect.any(String),
      model: expect.any(String),
      messages: expect.any(Array),
      createdAt: expect.any(String)
    })
  })

  it('healthCheck preserves backward-compatible response shape', async () => {
    const mockResponse = { status: 'healthy', timestamp: '2025-01-15T10:00:00Z' }
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
      status: 200
    })

    const result = await client.healthCheck()

    expect(result).toMatchObject({
      status: expect.any(String),
      timestamp: expect.any(String)
    })
  })

  it('retryPolicy preserves backward-compatible defaults', () => {
    const client = new AstrovoxClient({ apiKey: 'test' })
    const clientObj = client as any
    expect(clientObj.retryPolicy).toBeDefined()
    expect(clientObj.retryPolicy.maxRetries).toBeGreaterThanOrEqual(0)
    expect(clientObj.retryPolicy.retryableStatuses).toContain(429)
    expect(clientObj.retryPolicy.retryableStatuses).toContain(500)
  })

  it('baseUrl preserves trailing-slash normalization', () => {
    const client = new AstrovoxClient({ apiKey: 'test', baseUrl: 'https://api.example.com/' })
    expect((client as any).baseUrl).toBe('https://api.example.com')
  })

  it('request preserves Authorization header format', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: 'healthy' }),
      status: 200
    })

    await client.healthCheck()
    const headers = (fetch as any).mock.calls[0][1].headers
    expect(headers.Authorization).toBe('Bearer test-api-key')
    expect(headers['Content-Type']).toBe('application/json')
  })

  it('error messages preserve HTTP status and response text', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      text: () => Promise.resolve('Server error')
    })

    await expect(client.sendMessage({ conversationId: '1', message: 'Hello' })).rejects.toThrow('HTTP 500')
  })

  it('streamMessage preserves backward-compatible async generator interface', async () => {
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

    const stream = client.streamMessage({ conversationId: '1', message: 'Hello' })
    expect(typeof stream[Symbol.asyncIterator]).toBe('function')
    const chunks: string[] = []
    for await (const chunk of stream) {
      chunks.push(chunk)
    }
    expect(chunks.length).toBeGreaterThan(0)
  })

  it('createWebhook preserves backward-compatible response shape', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 'webhook-1', url: 'https://example.com', events: ['message.created'] }),
      status: 200
    })

    const result = await client.createWebhook({ url: 'https://example.com', events: ['message.created'] })
    expect(result).toHaveProperty('id')
    expect(result).toHaveProperty('url')
  })

  it('listWebhooks preserves backward-compatible response shape', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([{ id: 'webhook-1', url: 'https://example.com' }]),
      status: 200
    })

    const result = await client.listWebhooks()
    expect(Array.isArray(result)).toBe(true)
    expect(result[0]).toHaveProperty('id')
  })

  it('authenticateWithProvider preserves backward-compatible response shape', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ provider: 'google', token: 'mock-token' }),
      status: 200
    })

    const result = await client.authenticateWithProvider('google', 'mock-token')
    expect(result).toHaveProperty('provider')
    expect(result).toHaveProperty('token')
  })
})
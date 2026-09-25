import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AstrovoxClient } from '../sdk/typescript'

describe('API Contract Tests', () => {
  let client: AstrovoxClient

  beforeEach(() => {
    client = new AstrovoxClient({ apiKey: 'test-api-key' })
    vi.clearAllMocks()
  })

  it('sendMessage matches API contract', async () => {
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
    expect(result.ai_message).toHaveProperty('id')
    expect(result.ai_message).toHaveProperty('role', 'assistant')
    expect(result.ai_message).toHaveProperty('content')
    expect(result.ai_message).toHaveProperty('created_at')
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/chat/message'),
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          'Authorization': 'Bearer test-api-key',
          'Content-Type': 'application/json'
        })
      })
    )
  })

  it('createConversation matches API contract', async () => {
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

    expect(result).toHaveProperty('id')
    expect(result).toHaveProperty('title')
    expect(result).toHaveProperty('model')
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/conversations'),
      expect.objectContaining({
        method: 'POST',
        body: expect.stringContaining('"title":"New Conversation"')
      })
    )
  })

  it('listConversations matches API contract', async () => {
    const mockResponse = [
      { id: 'conv-1', title: 'Chat 1', model: 'gpt-4' },
      { id: 'conv-2', title: 'Chat 2', model: 'gpt-4' }
    ]
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
      status: 200
    })

    const result = await client.listConversations()

    expect(Array.isArray(result)).toBe(true)
    expect(result).toHaveLength(2)
    expect(result[0]).toHaveProperty('id')
    expect(result[0]).toHaveProperty('title')
  })

  it('handles authentication errors', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      statusText: 'Unauthorized'
    })

    await expect(client.sendMessage({ conversationId: 'conv-1', message: 'Hello' })).rejects.toThrow()
  })

  it('handles rate limiting', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 429,
      statusText: 'Too Many Requests'
    })

    await expect(client.sendMessage({ conversationId: 'conv-1', message: 'Hello' })).rejects.toThrow()
  })
})

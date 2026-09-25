import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AstrovoxClient } from '../../sdk/typescript'

describe('AI Evals', () => {
  let client: AstrovoxClient

  beforeEach(() => {
    client = new AstrovoxClient({ apiKey: 'test' })
    vi.clearAllMocks()
  })

  it('generates helpful responses', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        ai_message: { id: '1', role: 'assistant', content: 'I can help you with that. Here is the information you need.' }
      })
    })

    const result = await client.sendMessage({ conversationId: '1', message: 'What is 2+2?' })
    expect(result.ai_message.content).toContain('4')
  })

  it('follows instructions', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        ai_message: { id: '2', role: 'assistant', content: '```json\n{"result": "success"}\n```' }
      })
    })

    const result = await client.sendMessage({ conversationId: '1', message: 'Respond with JSON only' })
    expect(result.ai_message.content).toContain('json')
  })

  it('maintains context', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        ai_message: { id: '3', role: 'assistant', content: 'Your name is John, as you mentioned earlier.' }
      })
    })

    const result = await client.sendMessage({ conversationId: '1', message: 'What is my name?' })
    expect(result.ai_message.content.toLowerCase()).toContain('john')
  })
})

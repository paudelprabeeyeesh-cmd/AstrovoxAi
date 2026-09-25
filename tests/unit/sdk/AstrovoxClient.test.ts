import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AstrovoxClient } from '../../sdk/typescript'

describe('AstrovoxClient API surface', () => {
  let client: AstrovoxClient

  beforeEach(() => {
    client = new AstrovoxClient({ apiKey: 'test-api-key' })
    vi.clearAllMocks()
  })

  it('exposes sendMessage', () => {
    expect(typeof client.sendMessage).toBe('function')
  })

  it('exposes streamMessage', () => {
    expect(typeof client.streamMessage).toBe('function')
  })

  it('exposes createConversation', () => {
    expect(typeof client.createConversation).toBe('function')
  })

  it('exposes listConversations', () => {
    expect(typeof client.listConversations).toBe('function')
  })

  it('exposes getConversation', () => {
    expect(typeof client.getConversation).toBe('function')
  })

  it('exposes deleteConversation', () => {
    expect(typeof client.deleteConversation).toBe('function')
  })

  it('exposes createWebhook', () => {
    expect(typeof client.createWebhook).toBe('function')
  })

  it('exposes listWebhooks', () => {
    expect(typeof client.listWebhooks).toBe('function')
  })

  it('exposes deleteWebhook', () => {
    expect(typeof client.deleteWebhook).toBe('function')
  })

  it('exposes exportConversation', () => {
    expect(typeof client.exportConversation).toBe('function')
  })

  it('exposes importConversation', () => {
    expect(typeof client.importConversation).toBe('function')
  })

  it('exposes healthCheck', () => {
    expect(typeof client.healthCheck).toBe('function')
  })

  it('exposes authenticateWithProvider', () => {
    expect(typeof client.authenticateWithProvider).toBe('function')
  })

  it('exposes registerPlugin', () => {
    expect(typeof client.registerPlugin).toBe('function')
  })
})
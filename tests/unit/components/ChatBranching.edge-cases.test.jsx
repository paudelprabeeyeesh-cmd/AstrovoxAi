import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ChatBranching from '../../src/components/workspace/ChatBranching'

describe('ChatBranching - Edge Cases', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('handles no assistant messages', () => {
    render(<ChatBranching messages={[{ id: '1', role: 'user', content: 'Hello' }]} />)
    expect(screen.getByText(/no branches yet/i)).toBeDefined()
  })

  it('handles many branches', () => {
    const messages = Array.from({ length: 20 }, (_, i) => ({
      id: String(i),
      role: i % 2 === 0 ? 'user' : 'assistant',
      content: `Message ${i}`
    }))
    render(<ChatBranching messages={messages} />)
    expect(screen.getByText('Response 10')).toBeDefined()
  })

  it('handles empty message content', () => {
    const messages = [
      { id: '1', role: 'user', content: 'Hello' },
      { id: '2', role: 'assistant', content: '' }
    ]
    render(<ChatBranching messages={messages} />)
    expect(screen.getByText('Response 1')).toBeDefined()
  })
})

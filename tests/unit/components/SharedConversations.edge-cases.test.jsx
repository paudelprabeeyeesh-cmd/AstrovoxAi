import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import SharedConversations from '../../src/components/workspace/SharedConversations'

describe('SharedConversations - Edge Cases', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('handles empty shared list', () => {
    render(<SharedConversations sharedConversations={[]} />)
    expect(screen.getByText(/no shared conversations yet/i)).toBeDefined()
  })

  it('handles many shared conversations', () => {
    const many = Array.from({ length: 50 }, (_, i) => ({
      id: String(i),
      title: `Shared ${i}`,
      shared: i % 2 === 0,
      sharedWith: [{ name: `User ${i}`, email: `user${i}@example.com` }],
      sharedAt: new Date().toISOString()
    }))
    render(<SharedConversations sharedConversations={many} />)
    expect(screen.getByText('Shared 0')).toBeDefined()
  })
})

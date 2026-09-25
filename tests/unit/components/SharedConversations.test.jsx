import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import SharedConversations from '../../src/components/workspace/SharedConversations'

describe('SharedConversations', () => {
  const mockShared = [
    { id: '1', title: 'Shared Chat 1', shared: true, sharedWith: [{ name: 'Alice', email: 'alice@example.com' }], sharedAt: '2025-01-15T10:00:00Z' },
    { id: '2', title: 'Shared Chat 2', shared: true, sharedWith: [{ name: 'Bob', email: 'bob@example.com' }], sharedAt: '2025-01-14T10:00:00Z' }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders shared conversations', () => {
    render(<SharedConversations sharedConversations={mockShared} />)
    expect(screen.getByText('Shared Chat 1')).toBeDefined()
    expect(screen.getByText('Shared Chat 2')).toBeDefined()
  })

  it('filters by status', () => {
    render(<SharedConversations sharedConversations={mockShared} />)
    const filter = screen.getByRole('combobox')
    fireEvent.change(filter, { target: { value: 'shared' } })
    expect(screen.getByText('Shared Chat 1')).toBeDefined()
  })

  it('calls onOpen when conversation clicked', () => {
    const onOpen = vi.fn()
    render(<SharedConversations sharedConversations={mockShared} onOpen={onOpen} />)
    fireEvent.click(screen.getByText('Shared Chat 1'))
    expect(onOpen).toHaveBeenCalledWith('1')
  })

  it('calls onUnshare when unshare clicked', () => {
    const onUnshare = vi.fn()
    render(<SharedConversations sharedConversations={mockShared} onUnshare={onUnshare} />)
    const unshareButtons = screen.getAllByRole('button', { name: /unshare/i })
    fireEvent.click(unshareButtons[0])
    expect(onUnshare).toHaveBeenCalledWith('1')
  })
})

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import MultiChatTabs from '../src/components/workspace/MultiChatTabs'

describe('MultiChatTabs', () => {
  const mockConversations = [
    { id: '1', title: 'Chat 1' },
    { id: '2', title: 'Chat 2' },
    { id: '3', title: 'Chat 3' }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders all tabs', () => {
    render(<MultiChatTabs conversations={mockConversations} activeId="1" onSelect={() => {}} />)
    expect(screen.getByText('Chat 1')).toBeDefined()
    expect(screen.getByText('Chat 2')).toBeDefined()
    expect(screen.getByText('Chat 3')).toBeDefined()
  })

  it('highlights active tab', () => {
    render(<MultiChatTabs conversations={mockConversations} activeId="2" onSelect={() => {}} />)
    expect(screen.getByRole('tab', { name: /chat: chat 2/i })).toHaveAttribute('aria-selected', 'true')
  })

  it('calls onSelect when tab clicked', () => {
    const onSelect = vi.fn()
    render(<MultiChatTabs conversations={mockConversations} activeId="1" onSelect={onSelect} />)
    fireEvent.click(screen.getByRole('tab', { name: /chat: chat 2/i }))
    expect(onSelect).toHaveBeenCalledWith('2')
  })

  it('calls onNew when new button clicked', () => {
    const onNew = vi.fn()
    render(<MultiChatTabs conversations={mockConversations} activeId="1" onSelect={() => {}} onNew={onNew} />)
    fireEvent.click(screen.getByRole('button', { name: /new chat tab/i }))
    expect(onNew).toHaveBeenCalled()
  })
})

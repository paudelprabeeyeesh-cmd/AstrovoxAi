import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import MultiChatTabs from '../../src/components/workspace/MultiChatTabs'

describe('MultiChatTabs - Advanced', () => {
  const mockConversations = [
    { id: '1', title: 'Chat 1' },
    { id: '2', title: 'Chat 2' },
    { id: '3', title: 'Chat 3' }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renames tab on double click', () => {
    render(<MultiChatTabs conversations={mockConversations} activeId="1" onSelect={() => {}} onNew={() => {}} />)
    const tab = screen.getByRole('tab', { name: /chat: chat 1/i })
    fireEvent.doubleClick(tab)
    expect(screen.getByRole('textbox')).toBeDefined()
  })

  it('closes tab when close button clicked', () => {
    const onClose = vi.fn()
    render(<MultiChatTabs conversations={mockConversations} activeId="1" onSelect={() => {}} onNew={() => {}} onClose={onClose} />)
    const closeButtons = screen.getAllByRole('button', { name: /close/i })
    fireEvent.click(closeButtons[0])
    expect(onClose).toHaveBeenCalledWith('1')
  })

  it('prevents closing last tab', () => {
    render(<MultiChatTabs conversations={[{ id: '1', title: 'Only Chat' }]} activeId="1" onSelect={() => {}} onNew={() => {}} />)
    expect(screen.queryByRole('button', { name: /close/i })).toBeNull()
  })
})

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ChatBranching from '../../src/components/workspace/ChatBranching'

describe('ChatBranching', () => {
  const mockMessages = [
    { id: '1', role: 'user', content: 'Hello' },
    { id: '2', role: 'assistant', content: 'Hi there! How can I help?' },
    { id: '3', role: 'user', content: 'Tell me about AI' },
    { id: '4', role: 'assistant', content: 'AI is artificial intelligence...' }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders branch points', () => {
    render(<ChatBranching messages={mockMessages} />)
    expect(screen.getByText('Response 1')).toBeDefined()
    expect(screen.getByText('Response 2')).toBeDefined()
  })

  it('calls onCreateBranch when branch button clicked', () => {
    const onCreateBranch = vi.fn()
    render(<ChatBranching messages={mockMessages} onCreateBranch={onCreateBranch} />)
    const branchButtons = screen.getAllByRole('button', { name: /branch/i })
    fireEvent.click(branchButtons[0])
    expect(onCreateBranch).toHaveBeenCalledWith('2')
  })

  it('shows empty state when no branches', () => {
    render(<ChatBranching messages={[{ id: '1', role: 'user', content: 'Hello' }]} />)
    expect(screen.getByText(/no branches yet/i)).toBeDefined()
  })
})

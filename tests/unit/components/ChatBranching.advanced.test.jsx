import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ChatBranching from '../../src/components/workspace/ChatBranching'

describe('ChatBranching - Advanced', () => {
  const mockMessages = [
    { id: '1', role: 'user', content: 'Hello' },
    { id: '2', role: 'assistant', content: 'Hi there! How can I help you today?' },
    { id: '3', role: 'user', content: 'Tell me about AI' },
    { id: '4', role: 'assistant', content: 'AI is artificial intelligence...' }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('creates branch from specific message', () => {
    const onCreateBranch = vi.fn()
    render(<ChatBranching messages={mockMessages} onCreateBranch={onCreateBranch} />)
    const branchButtons = screen.getAllByRole('button', { name: /branch/i })
    fireEvent.click(branchButtons[0])
    expect(onCreateBranch).toHaveBeenCalledWith('2')
  })

  it('calls onBranchSelect', () => {
    const onBranchSelect = vi.fn()
    render(<ChatBranching messages={mockMessages} onBranchSelect={onBranchSelect} />)
    const viewButtons = screen.getAllByRole('button', { name: /view/i })
    fireEvent.click(viewButtons[0])
    expect(onBranchSelect).toHaveBeenCalledWith('2')
  })

  it('shows correct branch count', () => {
    render(<ChatBranching messages={mockMessages} />)
    expect(screen.getByText('Response 1')).toBeDefined()
    expect(screen.getByText('Response 2')).toBeDefined()
  })
})

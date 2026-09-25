import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import MessageActions from '../src/components/chat/MessageActions'

describe('MessageActions', () => {
  const mockMessage = {
    id: '1',
    role: 'user',
    content: 'Test message',
    timestamp: new Date().toISOString()
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders message actions', () => {
    render(<MessageActions message={mockMessage} />)
    expect(screen.getByRole('button', { name: /copy message/i })).toBeDefined()
  })

  it('shows edit button for user messages', () => {
    render(<MessageActions message={mockMessage} onEdit={() => {}} />)
    expect(screen.getByRole('button', { name: /edit message/i })).toBeDefined()
  })

  it('shows retry button for assistant messages', () => {
    const assistantMessage = { ...mockMessage, role: 'assistant' }
    render(<MessageActions message={assistantMessage} onRetry={() => {}} />)
    expect(screen.getByRole('button', { name: /retry/i })).toBeDefined()
  })

  it('opens more menu', () => {
    render(<MessageActions message={mockMessage} onBranch={() => {}} onDelete={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: /more actions/i }))
    expect(screen.getByText('Branch from here')).toBeDefined()
    expect(screen.getByText('Delete')).toBeDefined()
  })

  it('calls onCopy when copy clicked', async () => {
    const onCopy = vi.fn()
    render(<MessageActions message={mockMessage} onCopy={onCopy} />)
    fireEvent.click(screen.getByRole('button', { name: /copy message/i }))
    expect(onCopy).toHaveBeenCalledWith(mockMessage)
  })
})

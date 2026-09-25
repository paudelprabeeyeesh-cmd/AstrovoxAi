import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ChatInterface from '../../src/components/chat/ChatInterface'
import { A11yProvider } from '../../src/components/ui/A11yProvider'

const mockSession = {
  user: { id: 'test-user', email: 'test@example.com' }
}

describe('ChatInterface', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders chat interface', () => {
    render(
      <A11yProvider>
        <ChatInterface session={mockSession} conversationId="conv-1" model="gpt-4" />
      </A11yProvider>
    )
    expect(screen.getByRole('log')).toBeDefined()
  })

  it('shows empty state when no messages', () => {
    render(
      <A11yProvider>
        <ChatInterface session={mockSession} conversationId="conv-1" model="gpt-4" />
      </A11yProvider>
    )
    expect(screen.getByText(/start a conversation/i)).toBeDefined()
  })

  it('has accessible send button', () => {
    render(
      <A11yProvider>
        <ChatInterface session={mockSession} conversationId="conv-1" model="gpt-4" />
      </A11yProvider>
    )
    const sendButton = screen.getByRole('button', { name: /send/i })
    expect(sendButton).toBeDefined()
    expect(sendButton.hasAttribute('aria-label')).toBe(true)
  })

  it('has accessible message input', () => {
    render(
      <A11yProvider>
        <ChatInterface session={mockSession} conversationId="conv-1" model="gpt-4" />
      </A11yProvider>
    )
    const input = screen.getByRole('textbox', { name: /message input/i })
    expect(input).toBeDefined()
  })
})

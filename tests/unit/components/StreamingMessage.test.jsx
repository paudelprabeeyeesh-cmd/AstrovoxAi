import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import StreamingMessage from '../../src/components/chat/StreamingMessage'

describe('StreamingMessage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders complete message', () => {
    render(<StreamingMessage content="Hello world" isComplete={true} />)
    expect(screen.getByText('Hello world')).toBeDefined()
  })

  it('shows typing indicator when streaming', () => {
    render(<StreamingMessage content="Hello" isComplete={false} />)
    expect(screen.getByText(/listening/i)).toBeDefined()
  })

  it('displays model name', () => {
    render(<StreamingMessage content="Test" isComplete={true} model="gpt-4" />)
    expect(screen.getByText('gpt-4')).toBeDefined()
  })

  it('shows retry button when onRetry provided', () => {
    const onRetry = vi.fn()
    render(<StreamingMessage content="Test" isComplete={true} onRetry={onRetry} />)
    const retryButton = screen.getByRole('button', { name: /retry/i })
    expect(retryButton).toBeDefined()
    fireEvent.click(retryButton)
    expect(onRetry).toHaveBeenCalled()
  })
})

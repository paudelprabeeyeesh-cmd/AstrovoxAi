import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import StreamingMessage from '../../src/components/chat/StreamingMessage'

describe('StreamingMessage - Edge Cases', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders empty content', () => {
    render(<StreamingMessage content="" isComplete={true} />)
    expect(screen.queryByText('')).toBeDefined()
  })

  it('renders very long content', () => {
    const longContent = 'A'.repeat(10000)
    render(<StreamingMessage content={longContent} isComplete={true} />)
    expect(screen.getByText(longContent)).toBeDefined()
  })

  it('handles special characters', () => {
    const special = '<script>alert("xss")</script>'
    render(<StreamingMessage content={special} isComplete={true} />)
    expect(screen.getByText(special)).toBeDefined()
  })

  it('shows model name', () => {
    render(<StreamingMessage content="test" isComplete={true} model="claude-3-opus" />)
    expect(screen.getByText('claude-3-opus')).toBeDefined()
  })
})

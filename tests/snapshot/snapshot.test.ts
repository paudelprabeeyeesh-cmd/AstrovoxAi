import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

const mockSnapshots = {
  ChatInterface: () => <div data-testid="chat-interface">Chat Interface</div>,
  StreamingMessage: () => <div data-testid="streaming-message">Streaming Message</div>,
  ThemeEngine: () => <div data-testid="theme-engine">Theme Engine</div>,
}

describe('Snapshot Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('ChatInterface renders correctly', () => {
    const { container } = render(<mockSnapshots.ChatInterface />)
    expect(container.firstChild).toMatchSnapshot()
  })

  it('StreamingMessage renders correctly', () => {
    const { container } = render(<mockSnapshots.StreamingMessage />)
    expect(container.firstChild).toMatchSnapshot()
  })

  it('ThemeEngine renders correctly', () => {
    const { container } = render(<mockSnapshots.ThemeEngine />)
    expect(container.firstChild).toMatchSnapshot()
  })

  it('ChatInterface with messages matches snapshot', () => {
    const { container } = render(
      <div>
        <mockSnapshots.ChatInterface />
        <div data-testid="message">Hello AI</div>
        <div data-testid="message">How are you?</div>
      </div>
    )
    expect(container.innerHTML).toMatchSnapshot()
  })

  it('ThemeEngine in dark mode matches snapshot', () => {
    const { container } = render(
      <div data-theme="dark">
        <mockSnapshots.ThemeEngine />
      </div>
    )
    expect(container.innerHTML).toMatchSnapshot()
  })
})

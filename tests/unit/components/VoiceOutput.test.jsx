import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import VoiceOutput from '../../src/components/chat/VoiceOutput'

describe('VoiceOutput', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders nothing without text', () => {
    const { container } = render(<VoiceOutput text="" />)
    expect(container.firstChild).toBeNull()
  })

  it('renders play button with text', () => {
    render(<VoiceOutput text="Hello world" />)
    expect(screen.getByRole('button', { name: /play/i })).toBeDefined()
  })

  it('shows "Text to Speech" label when not playing', () => {
    render(<VoiceOutput text="Hello world" />)
    expect(screen.getByText('Text to Speech')).toBeDefined()
  })

  it('calls speechSynthesis.speak when play clicked', () => {
    const mockSpeak = vi.fn()
    const mockGetVoices = vi.fn(() => [])
    ;(window as any).speechSynthesis = { speak: mockSpeak, pause: vi.fn(), resume: vi.fn(), cancel: vi.fn(), getVoices: mockGetVoices }
    render(<VoiceOutput text="Hello world" />)
    fireEvent.click(screen.getByRole('button', { name: /play/i }))
    expect(mockSpeak).toHaveBeenCalled()
  })
})

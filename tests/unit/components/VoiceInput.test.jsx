import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import VoiceInput from '../../src/components/chat/VoiceInput'

describe('VoiceInput', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders microphone button', () => {
    render(<VoiceInput onTranscript={() => {}} onToggleListening={() => {}} />)
    expect(screen.getByRole('button', { name: /start listening/i })).toBeDefined()
  })

  it('shows listening state', () => {
    render(<VoiceInput onTranscript={() => {}} onToggleListening={() => {}} isListening={true} />)
    expect(screen.getByText(/listening/i)).toBeDefined()
  })

  it('shows error for unsupported browser', () => {
    render(<VoiceInput onTranscript={() => {}} onToggleListening={() => {}} />)
    expect(screen.getByText(/speech recognition not supported/i)).toBeDefined()
  })
})

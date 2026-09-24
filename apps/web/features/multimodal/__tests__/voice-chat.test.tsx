import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { VoiceChat } from '../voice-chat'

describe('VoiceChat', () => {
  beforeEach(() => {
    ;(window as any).SpeechRecognition = undefined
    ;(window as any).webkitSpeechRecognition = undefined
    ;(navigator as any).mediaDevices = { getUserMedia: jest.fn().mockResolvedValue({ getTracks: () => [] }) }
    ;(window as any).speechSynthesis = { speak: jest.fn(), cancel: jest.fn() }
  })

  it('renders microphone button', () => {
    render(<VoiceChat />)
    expect(screen.getByTitle('Start voice input')).toBeDefined()
  })

  it('calls onTranscribe on stop', async () => {
    const onTranscribe = jest.fn()
    render(<VoiceChat onTranscribe={onTranscribe} />)
    const btn = screen.getByTitle('Start voice input')
    fireEvent.click(btn)
    expect(screen.getByTitle('Stop recording')).toBeDefined()
  })

  it('shows play button after transcript is available', async () => {
    render(<VoiceChat autoSend={false} />)
    const btn = screen.getByTitle('Start voice input')
    fireEvent.click(btn)
  })

  it('calls onSynthesize when speak is triggered', () => {
    const onSynthesize = jest.fn()
    render(<VoiceChat onSynthesize={onSynthesize} />)
    const btn = screen.getByTitle('Start voice input')
    fireEvent.click(btn)
  })

  it('returns null when not supported', () => {
    const originalGetUserMedia = navigator.mediaDevices?.getUserMedia
    ;(navigator as any).mediaDevices = undefined
    const { container } = render(<VoiceChat />)
    expect(container.innerHTML).toBe('')
    ;(navigator as any).mediaDevices = originalGetUserMedia
  })

  it('disables button when disabled prop is true', () => {
    render(<VoiceChat disabled />)
    const btn = screen.getByTitle('Start voice input')
    expect(btn).toHaveClass('opacity-50')
  })
})

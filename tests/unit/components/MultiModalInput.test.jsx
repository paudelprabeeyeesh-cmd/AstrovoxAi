import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MultiModalInput from '../src/components/MultiModalInput'

describe('MultiModalInput', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders text input', () => {
    render(<MultiModalInput onSend={() => {}} />)
    expect(screen.getByPlaceholderText(/message astrovox/i)).toBeDefined()
  })

  it('renders mode buttons', () => {
    render(<MultiModalInput onSend={() => {}} />)
    expect(screen.getByRole('button', { name: /text/i })).toBeDefined()
    expect(screen.getByRole('button', { name: /voice/i })).toBeDefined()
    expect(screen.getByRole('button', { name: /image/i })).toBeDefined()
    expect(screen.getByRole('button', { name: /file/i })).toBeDefined()
    expect(screen.getByRole('button', { name: /screen/i })).toBeDefined()
  })

  it('sends message on Enter', async () => {
    const onSend = vi.fn()
    render(<MultiModalInput onSend={onSend} />)
    const input = screen.getByPlaceholderText(/message astrovox/i)
    await userEvent.type(input, 'Hello world{Enter}')
    expect(onSend).toHaveBeenCalledWith(
      expect.objectContaining({ content: 'Hello world', mode: 'text' })
    )
  })

  it('does not send empty message', async () => {
    const onSend = vi.fn()
    render(<MultiModalInput onSend={onSend} />)
    const input = screen.getByPlaceholderText(/message astrovox/i)
    await userEvent.type(input, '{Enter}')
    expect(onSend).not.toHaveBeenCalled()
  })

  it('shows send button disabled when empty', () => {
    render(<MultiModalInput onSend={() => {}} />)
    const sendButton = screen.getByRole('button', { name: /send/i })
    expect(sendButton).toBeDisabled()
  })

  it('enables send button when input has text', async () => {
    render(<MultiModalInput onSend={() => {}} />)
    const input = screen.getByPlaceholderText(/message astrovox/i)
    await userEvent.type(input, 'test')
    const sendButton = screen.getByRole('button', { name: /send/i })
    expect(sendButton).not.toBeDisabled()
  })

  it('shows voice mode when voice button is clicked', async () => {
    render(<MultiModalInput onSend={() => {}} />)
    const voiceButton = screen.getByRole('button', { name: /voice/i })
    await userEvent.click(voiceButton)
    expect(screen.getByText(/listening/i)).toBeDefined()
  })

  it('shows file upload when file button is clicked', async () => {
    render(<MultiModalInput onSend={() => {}} />)
    const fileButton = screen.getByRole('button', { name: /file/i })
    await userEvent.click(fileButton)
    expect(screen.getByText(/drag and drop/i)).toBeDefined()
  })

  it('disables input when disabled prop is true', () => {
    render(<MultiModalInput onSend={() => {}} disabled={true} />)
    expect(screen.getByPlaceholderText(/message astrovox/i)).toBeDisabled()
  })
})

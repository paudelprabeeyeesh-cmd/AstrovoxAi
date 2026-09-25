import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import MediaEmbed from '../../src/components/chat/MediaEmbed'

describe('MediaEmbed', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders image', () => {
    render(<MediaEmbed type="image" src="https://example.com/image.png" alt="Test image" />)
    const img = screen.getByRole('img')
    expect(img).toBeDefined()
    expect(img.getAttribute('alt')).toBe('Test image')
  })

  it('renders audio', () => {
    render(<MediaEmbed type="audio" src="https://example.com/audio.mp3" />)
    const audio = document.querySelector('audio')
    expect(audio).toBeDefined()
  })

  it('renders video', () => {
    render(<MediaEmbed type="video" src="https://example.com/video.mp4" />)
    const video = document.querySelector('video')
    expect(video).toBeDefined()
  })

  it('renders file download', () => {
    render(<MediaEmbed type="file" src="https://example.com/file.pdf" alt="PDF Document" />)
    expect(screen.getByText('PDF Document')).toBeDefined()
    expect(screen.getByText('Click to download')).toBeDefined()
  })

  it('shows error state', () => {
    render(<MediaEmbed type="image" src="invalid-url" alt="Test" />)
    expect(screen.getByText(/failed to load/i)).toBeDefined()
  })
})

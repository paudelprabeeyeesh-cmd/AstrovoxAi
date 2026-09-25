import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ScreenShare from '../../src/components/chat/ScreenShare'

describe('ScreenShare', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(navigator as any).mediaDevices = {
      getDisplayMedia: vi.fn().mockResolvedValue({
        getTracks: () => [{ stop: vi.fn(), onended: null }]
      })
    }
  })

  it('renders screen share panel', () => {
    render(<ScreenShare onShare={() => {}} onClose={() => {}} />)
    expect(screen.getByText('Screen Share')).toBeDefined()
  })

  it('shows start sharing button when not sharing', () => {
    render(<ScreenShare onShare={() => {}} onClose={() => {}} />)
    expect(screen.getByRole('button', { name: /start sharing/i })).toBeDefined()
  })

  it('calls onClose when close button clicked', () => {
    const onClose = vi.fn()
    render(<ScreenShare onShare={() => {}} onClose={onClose} />)
    fireEvent.click(screen.getByRole('button', { name: /close screen share/i }))
    expect(onClose).toHaveBeenCalled()
  })
})

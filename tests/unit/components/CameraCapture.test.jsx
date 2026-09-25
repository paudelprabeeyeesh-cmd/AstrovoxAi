import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import CameraCapture from '../../src/components/chat/CameraCapture'

describe('CameraCapture', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(navigator as any).mediaDevices = {
      getUserMedia: vi.fn().mockResolvedValue({
        getTracks: () => [{ stop: vi.fn() }]
      })
    }
  })

  it('renders camera view', () => {
    render(<CameraCapture onCapture={() => {}} onClose={() => {}} />)
    expect(screen.getByRole('button', { name: /close camera/i })).toBeDefined()
  })

  it('shows error when camera not available', async () => {
    ;(navigator as any).mediaDevices = {
      getUserMedia: vi.fn().mockRejectedValue(new Error('Permission denied'))
    }
    render(<CameraCapture onCapture={() => {}} onClose={() => {}} />)
    expect(screen.getByText(/camera error/i)).toBeDefined()
  })

  it('calls onClose when close button clicked', () => {
    const onClose = vi.fn()
    render(<CameraCapture onCapture={() => {}} onClose={onClose} />)
    fireEvent.click(screen.getByRole('button', { name: /close camera/i }))
    expect(onClose).toHaveBeenCalled()
  })
})

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { copyToClipboard } from '../../src/utils/clipboard'

describe('clipboard utils', () => {
  it('copyToClipboard uses navigator clipboard when available', async () => {
    const mockWriteText = vi.fn().mockResolvedValue(undefined)
    const originalClipboard = navigator.clipboard
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: mockWriteText },
      writable: true,
      configurable: true
    })

    const result = await copyToClipboard('test-text')
    expect(result.success).toBe(true)
    expect(mockWriteText).toHaveBeenCalledWith('test-text')

    Object.defineProperty(navigator, 'clipboard', {
      value: originalClipboard,
      writable: true,
      configurable: true
    })
  })

  it('copyToClipboard falls back when navigator clipboard is unavailable', async () => {
    const originalClipboard = navigator.clipboard
    Object.defineProperty(navigator, 'clipboard', {
      value: undefined,
      writable: true,
      configurable: true
    })

    const mockExecCommand = vi.fn().mockReturnValue(true)
    const originalExecCommand = document.execCommand
    document.execCommand = mockExecCommand

    const result = await copyToClipboard('fallback-text')
    expect(result.success).toBe(true)
    expect(mockExecCommand).toHaveBeenCalledWith('copy')

    document.execCommand = originalExecCommand
    Object.defineProperty(navigator, 'clipboard', {
      value: originalClipboard,
      writable: true,
      configurable: true
    })
  })

  it('copyToClipboard returns failure when fallback fails', async () => {
    const originalClipboard = navigator.clipboard
    Object.defineProperty(navigator, 'clipboard', {
      value: undefined,
      writable: true,
      configurable: true
    })

    const originalExecCommand = document.execCommand
    document.execCommand = vi.fn().mockReturnValue(false)

    const result = await copyToClipboard('fail-text')
    expect(result.success).toBe(false)

    document.execCommand = originalExecCommand
    Object.defineProperty(navigator, 'clipboard', {
      value: originalClipboard,
      writable: true,
      configurable: true
    })
  })
})
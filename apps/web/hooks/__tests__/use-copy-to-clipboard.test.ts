import React from 'react'
import { renderHook, act } from '@testing-library/react'
import { useCopyToClipboard } from '@/hooks/use-copy-to-clipboard'

describe('useCopyToClipboard', () => {
  const mockClipboard = {
    writeText: jest.fn(),
  }

  beforeEach(() => {
    Object.defineProperty(navigator, 'clipboard', {
      value: mockClipboard,
      configurable: true,
    })
    jest.useFakeTimers()
  })

  afterEach(() => {
    jest.useRealTimers()
    jest.clearAllMocks()
  })

  it('copies text to clipboard', async () => {
    mockClipboard.writeText.mockResolvedValue(undefined)
    const { result } = renderHook(() => useCopyToClipboard())

    await act(async () => {
      await result.current.copy('test text')
    })

    expect(mockClipboard.writeText).toHaveBeenCalledWith('test text')
    expect(result.current.isCopied).toBe(true)
  })

  it('resets copied state after delay', async () => {
    mockClipboard.writeText.mockResolvedValue(undefined)
    const { result } = renderHook(() => useCopyToClipboard(1000))

    await act(async () => {
      await result.current.copy('test text')
    })

    expect(result.current.isCopied).toBe(true)

    act(() => {
      jest.advanceTimersByTime(1000)
    })

    expect(result.current.isCopied).toBe(false)
  })

  it('handles clipboard errors gracefully', async () => {
    mockClipboard.writeText.mockRejectedValue(new Error('Clipboard error'))
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation()
    const { result } = renderHook(() => useCopyToClipboard())

    await act(async () => {
      await result.current.copy('test text')
    })

    expect(consoleSpy).toHaveBeenCalled()
    expect(result.current.isCopied).toBe(false)

    consoleSpy.mockRestore()
  })
})

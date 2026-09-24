import React from 'react'
import { renderHook, act } from '@testing-library/react'
import { useKeyboardShortcut } from '@/hooks/use-keyboard-shortcut'

describe('useKeyboardShortcut', () => {
  it('calls callback on key press', () => {
    const callback = jest.fn()
    renderHook(() => useKeyboardShortcut('k', callback, { ctrl: true }))

    act(() => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true }))
    })

    expect(callback).toHaveBeenCalledTimes(1)
  })

  it('does not call callback without modifiers when required', () => {
    const callback = jest.fn()
    renderHook(() => useKeyboardShortcut('k', callback, { ctrl: true }))

    act(() => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k' }))
    })

    expect(callback).not.toHaveBeenCalled()
  })

  it('calls callback with shift modifier', () => {
    const callback = jest.fn()
    renderHook(() => useKeyboardShortcut('k', callback, { shift: true }))

    act(() => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', shiftKey: true }))
    })

    expect(callback).toHaveBeenCalledTimes(1)
  })

  it('calls callback with multiple modifiers', () => {
    const callback = jest.fn()
    renderHook(() => useKeyboardShortcut('k', callback, { ctrl: true, shift: true }))

    act(() => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true, shiftKey: true }))
    })

    expect(callback).toHaveBeenCalledTimes(1)
  })
})

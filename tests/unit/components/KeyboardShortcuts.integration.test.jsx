import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { useKeyboardShortcuts } from '../../src/components/ui/KeyboardShortcuts'

describe('KeyboardShortcuts - Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(window, 'addEventListener').mockImplementation(() => {})
  })

  it('registers keyboard shortcuts', () => {
    const handler = vi.fn()
    function TestComponent() {
      useKeyboardShortcuts({ custom: { keys: ['c'], ctrl: true, handler } })
      return null
    }
    render(<TestComponent />)
    expect(window.addEventListener).toHaveBeenCalledWith('keydown', expect.any(Function))
  })

  it('triggers custom shortcut on Ctrl+C', () => {
    const handler = vi.fn()
    function TestComponent() {
      useKeyboardShortcuts({ custom: { keys: ['c'], ctrl: true, handler } })
      return null
    }
    render(<TestComponent />)
    fireEvent.keyDown(window, { key: 'c', ctrlKey: true })
    expect(handler).toHaveBeenCalled()
  })
})

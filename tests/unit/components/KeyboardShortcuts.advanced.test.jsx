import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { useKeyboardShortcuts, useFocusManagement } from '../../src/components/ui/KeyboardShortcuts'
import { A11yProvider } from '../../src/components/ui/A11yProvider'

describe('KeyboardShortcuts - Advanced', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('useFocusManagement provides focusFirstInteractive', () => {
    let focusFirstInteractive: any
    function TestComponent() {
      const { focusFirstInteractive } = useFocusManagement()
      focusFirstInteractive = focusFirstInteractive
      return (
        <div>
          <button>First</button>
          <button>Second</button>
        </div>
      )
    }
    render(
      <A11yProvider>
        <TestComponent />
      </A11yProvider>
    )
    expect(typeof focusFirstInteractive).toBe('function')
  })

  it('useFocusManagement provides trapFocus', () => {
    let trapFocus: any
    function TestComponent() {
      const { trapFocus } = useFocusManagement()
      trapFocus = trapFocus
      return (
        <div>
          <button>First</button>
          <button>Last</button>
        </div>
      )
    }
    render(
      <A11yProvider>
        <TestComponent />
      </A11yProvider>
    )
    expect(typeof trapFocus).toBe('function')
  })
})

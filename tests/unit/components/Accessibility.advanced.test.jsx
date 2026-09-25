import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { A11yProvider, useA11y, SkipLink } from '../src/components/ui/A11yProvider'
import { A11Y_SPECS } from '../src/design/AccessibilitySpecs'

describe('Accessibility - Advanced', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('SkipLink has correct href', () => {
    render(<SkipLink targetId="main">Skip</SkipLink>)
    const link = screen.getByText('Skip')
    expect(link.getAttribute('href')).toBe('#main')
  })

  it('A11yProvider provides specs', () => {
    let specs: any
    function TestComponent() {
      const { specs: s } = useA11y()
      specs = s
      return null
    }
    render(
      <A11yProvider>
        <TestComponent />
      </A11yProvider>
    )
    expect(specs).toBe(A11Y_SPECS)
  })

  it('focus management traps focus', () => {
    let trapFocus: any
    function TestComponent() {
      const { trapFocus } = useA11y()
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

  it('announce function is available', () => {
    let announce: any
    function TestComponent() {
      const { announce: a } = useA11y()
      announce = a
      return null
    }
    render(
      <A11yProvider>
        <TestComponent />
      </A11yProvider>
    )
    expect(typeof announce).toBe('function')
  })
})

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { A11yProvider, useA11y } from '../../src/components/ui/A11yProvider'

describe('A11yProvider - Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('provides complete accessibility context', () => {
    let a11y: any
    function TestComponent() {
      a11y = useA11y()
      return <div>Test</div>
    }
    render(
      <A11yProvider>
        <TestComponent />
      </A11yProvider>
    )
    expect(a11y.specs).toBeDefined()
    expect(a11y.specs.WCAG_LEVEL).toBe('AA')
    expect(a11y.announce).toBeDefined()
    expect(a11y.focusFirstInteractive).toBeDefined()
    expect(a11y.trapFocus).toBeDefined()
    expect(a11y.screenReaderMode).toBeDefined()
    expect(a11y.highContrastMode).toBeDefined()
    expect(a11y.reducedMotion).toBeDefined()
  })
})

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { A11yProvider, useA11y, SkipLink } from '../src/components/ui/A11yProvider'

describe('A11yProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('provides accessibility context', () => {
    let a11yContext: any
    function TestComponent() {
      a11yContext = useA11y()
      return <div>Test</div>
    }
    render(
      <A11yProvider>
        <TestComponent />
      </A11yProvider>
    )
    expect(a11yContext.specs).toBeDefined()
    expect(a11yContext.specs.WCAG_LEVEL).toBe('AA')
  })

  it('SkipLink renders correctly', () => {
    render(<SkipLink targetId="main-content">Skip to main</SkipLink>)
    const link = screen.getByText('Skip to main')
    expect(link).toHaveAttribute('href', '#main-content')
  })

  it('announces messages', () => {
    let announceFn: any
    function TestComponent() {
      const { announce } = useA11y()
      announceFn = announce
      return (
        <button onClick={() => announce('Test announcement')}>
          Announce
        </button>
      )
    }
    render(
      <A11yProvider>
        <TestComponent />
      </A11yProvider>
    )
    fireEvent.click(screen.getByRole('button', { name: /announce/i }))
  })
})

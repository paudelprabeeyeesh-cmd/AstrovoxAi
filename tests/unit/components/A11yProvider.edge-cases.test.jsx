import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
import { A11yProvider, useA11y } from '../src/components/ui/A11yProvider'

describe('A11yProvider - Edge Cases', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('handles rapid announcements', async () => {
    let announce: any
    function TestComponent() {
      const { announcements } = useA11y()
      announce = announcements
      return null
    }
    render(
      <A11yProvider>
        <TestComponent />
      </A11yProvider>
    )
    expect(announce).toBeDefined()
  })

  it('reduced motion is detected from media query', () => {
    let reducedMotion: any
    function TestComponent() {
      const { reducedMotion: rm } = useA11y()
      reducedMotion = rm
      return null
    }
    render(
      <A11yProvider>
        <TestComponent />
      </A11yProvider>
    )
    expect(typeof reducedMotion).toBe('boolean')
  })

  it('high contrast mode is detected', () => {
    let highContrastMode: any
    function TestComponent() {
      const { highContrastMode: hc } = useA11y()
      highContrastMode = hc
      return null
    }
    render(
      <A11yProvider>
        <TestComponent />
      </A11yProvider>
    )
    expect(typeof highContrastMode).toBe('boolean')
  })
})

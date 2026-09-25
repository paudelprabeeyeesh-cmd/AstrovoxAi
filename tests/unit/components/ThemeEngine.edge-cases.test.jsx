import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { useTheme, THEMES } from '../../src/design/DesignTokens'

describe('ThemeEngine - Edge Cases', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.getItem = vi.fn(() => 'astrovox')
    localStorage.setItem = vi.fn()
  })

  it('falls back to astrovox theme on invalid storage', () => {
    localStorage.getItem = vi.fn(() => 'nonexistent-theme')
    let themeName: any
    function TestComponent() {
      const { themeName: tn } = useTheme()
      themeName = tn
      return null
    }
    render(<TestComponent />)
    expect(themeName).toBe('astrovox')
  })

  it('ignores invalid theme names', () => {
    let themeName: any
    function TestComponent() {
      const { themeName: tn, setTheme } = useTheme()
      themeName = tn
      return <button onClick={() => setTheme('invalid-theme')}>Set</button>
    }
    render(<TestComponent />)
    fireEvent.click(screen.getByRole('button'))
    expect(themeName).toBe('astrovox')
  })

  it('has all required color properties in all themes', () => {
    const requiredColors = ['background', 'surface', 'border', 'text', 'primary', 'secondary', 'error', 'success', 'warning']
    for (const themeName of Object.keys(THEMES)) {
      const theme = THEMES[themeName]
      for (const color of requiredColors) {
        expect(theme.colors[color]).toBeDefined()
        expect(typeof theme.colors[color]).toBe('string')
      }
    }
  })
})

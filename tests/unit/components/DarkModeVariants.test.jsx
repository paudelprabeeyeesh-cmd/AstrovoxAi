import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ThemeEngine } from '../../src/components/ui/ThemeEngine'
import { THEMES, useTheme } from '../../src/design/DesignTokens'

describe('Dark Mode Variants', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.getItem = vi.fn(() => 'astrovox')
  })

  it('applies dark theme by default', () => {
    render(
      <ThemeEngine>
        <div>Test</div>
      </ThemeEngine>
    )
    const container = document.querySelector('[data-theme]')
    expect(container?.getAttribute('data-theme')).toBe('astrovox')
  })

  it('switches to light theme', () => {
    render(
      <ThemeEngine>
        <div>Test</div>
      </ThemeEngine>
    )
    fireEvent.click(screen.getByRole('button', { name: /toggle theme/i }))
    fireEvent.click(screen.getByText('Light'))
    const container = document.querySelector('[data-theme]')
    expect(container?.getAttribute('data-theme')).toBe('light')
  })

  it('switches to high contrast theme', () => {
    render(
      <ThemeEngine>
        <div>Test</div>
      </ThemeEngine>
    )
    fireEvent.click(screen.getByRole('button', { name: /toggle theme/i }))
    fireEvent.click(screen.getByText('High Contrast'))
    const container = document.querySelector('[data-theme]')
    expect(container?.getAttribute('data-theme')).toBe('highContrast')
  })

  it('persists theme preference', () => {
    render(
      <ThemeEngine>
        <div>Test</div>
      </ThemeEngine>
    )
    fireEvent.click(screen.getByRole('button', { name: /toggle theme/i }))
    fireEvent.click(screen.getByText('Light'))
    expect(localStorage.setItem).toHaveBeenCalledWith('astrovox-theme', 'light')
  })
})

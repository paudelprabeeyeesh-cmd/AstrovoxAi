import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ThemeEngine } from '../src/components/ui/ThemeEngine'
import { THEMES, useTheme } from '../src/design/DesignTokens'

describe('ThemeEngine', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.getItem = vi.fn(() => 'astrovox')
  })

  it('renders ThemeEngine with children', () => {
    render(
      <ThemeEngine>
        <div>Child Content</div>
      </ThemeEngine>
    )
    expect(screen.getByText('Child Content')).toBeDefined()
  })

  it('has theme switcher button', () => {
    render(
      <ThemeEngine>
        <div>Test</div>
      </ThemeEngine>
    )
    expect(screen.getByRole('button', { name: /toggle theme/i })).toBeDefined()
  })

  it('opens theme menu on click', () => {
    render(
      <ThemeEngine>
        <div>Test</div>
      </ThemeEngine>
    )
    fireEvent.click(screen.getByRole('button', { name: /toggle theme/i }))
    expect(screen.getByText('Astrovox Prime')).toBeDefined()
    expect(screen.getByText('Light')).toBeDefined()
    expect(screen.getByText('High Contrast')).toBeDefined()
  })
})

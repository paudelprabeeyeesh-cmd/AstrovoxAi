import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ThemeEngine } from '../src/components/ui/ThemeEngine'

describe('ThemeEngine', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.getItem = vi.fn(() => 'astrovox')
  })

  it('renders with default theme', () => {
    render(
      <ThemeEngine>
        <div>Test Content</div>
      </ThemeEngine>
    )
    expect(screen.getByText('Test Content')).toBeDefined()
  })

  it('has accessible theme switcher', () => {
    render(
      <ThemeEngine>
        <div>Test</div>
      </ThemeEngine>
    )
    const themeButton = screen.getByRole('button', { name: /toggle theme/i })
    expect(themeButton).toBeDefined()
    fireEvent.click(themeButton)
  })
})

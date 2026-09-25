import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { useTheme, THEMES } from '../../src/design/DesignTokens'

describe('DesignTokens', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.getItem = vi.fn(() => 'astrovox')
  })

  it('has astrovox theme', () => {
    expect(THEMES.astrovox).toBeDefined()
    expect(THEMES.astrovox.name).toBe('Astrovox Prime')
  })

  it('has light theme', () => {
    expect(THEMES.light).toBeDefined()
    expect(THEMES.light.name).toBe('Light')
  })

  it('has high contrast theme', () => {
    expect(THEMES.highContrast).toBeDefined()
    expect(THEMES.highContrast.name).toBe('High Contrast')
  })

  it('theme has required color properties', () => {
    const requiredColors = ['background', 'surface', 'border', 'text', 'primary', 'secondary', 'error', 'success', 'warning']
    for (const color of requiredColors) {
      expect(THEMES.astrovox.colors[color]).toBeDefined()
    }
  })

  it('theme has required font properties', () => {
    expect(THEMES.astrovox.fonts.sans).toBeDefined()
    expect(THEMES.astrovox.fonts.mono).toBeDefined()
  })

  it('theme has required radius properties', () => {
    expect(THEMES.astrovox.radius.sm).toBeDefined()
    expect(THEMES.astrovox.radius.md).toBeDefined()
    expect(THEMES.astrovox.radius.lg).toBeDefined()
  })
})

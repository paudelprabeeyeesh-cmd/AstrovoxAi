import { describe, it, expect } from 'vitest'
import { THEMES } from '../../src/design/DesignTokens'

describe('DesignTokens', () => {
  it('THEMES contains astrovox, light, and highContrast themes', () => {
    expect(THEMES).toHaveProperty('astrovox')
    expect(THEMES).toHaveProperty('light')
    expect(THEMES).toHaveProperty('highContrast')
  })

  it('astrovox theme has required color properties', () => {
    const colors = THEMES.astrovox.colors
    expect(colors).toHaveProperty('background')
    expect(colors).toHaveProperty('surface')
    expect(colors).toHaveProperty('primary')
    expect(colors).toHaveProperty('text')
    expect(colors).toHaveProperty('error')
  })

  it('light theme has required color properties', () => {
    const colors = THEMES.light.colors
    expect(colors).toHaveProperty('background')
    expect(colors).toHaveProperty('surface')
    expect(colors).toHaveProperty('primary')
    expect(colors).toHaveProperty('text')
    expect(colors).toHaveProperty('error')
  })

  it('highContrast theme has required color properties', () => {
    const colors = THEMES.highContrast.colors
    expect(colors).toHaveProperty('background')
    expect(colors).toHaveProperty('text')
    expect(colors).toHaveProperty('primary')
  })

  it('all themes have fonts, radius, and shadows', () => {
    for (const theme of Object.values(THEMES)) {
      expect(theme).toHaveProperty('fonts')
      expect(theme).toHaveProperty('radius')
      expect(theme).toHaveProperty('shadows')
    }
  })

  it('theme fonts include sans and mono', () => {
    for (const theme of Object.values(THEMES)) {
      expect(theme.fonts).toHaveProperty('sans')
      expect(theme.fonts).toHaveProperty('mono')
    }
  })

  it('theme radius has expected keys', () => {
    for (const theme of Object.values(THEMES)) {
      expect(theme.radius).toHaveProperty('sm')
      expect(theme.radius).toHaveProperty('md')
      expect(theme.radius).toHaveProperty('lg')
    }
  })

  it('theme shadows has expected keys', () => {
    for (const theme of Object.values(THEMES)) {
      expect(theme.shadows).toHaveProperty('sm')
      expect(theme.shadows).toHaveProperty('md')
      expect(theme.shadows).toHaveProperty('lg')
    }
  })

  it('each theme has a name', () => {
    expect(THEMES.astrovox.name).toBe('Astrovox Prime')
    expect(THEMES.light.name).toBe('Light')
    expect(THEMES.highContrast.name).toBe('High Contrast')
  })
})
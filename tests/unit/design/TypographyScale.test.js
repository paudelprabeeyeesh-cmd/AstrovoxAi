import { describe, it, expect } from 'vitest'
import { TYPOGRAPHY, useTypography } from '../../src/design/TypographyScale'

describe('TypographyScale', () => {
  it('TYPOGRAPHY has expected scale keys', () => {
    const scaleKeys = Object.keys(TYPOGRAPHY.scale)
    expect(scaleKeys).toContain('xs')
    expect(scaleKeys).toContain('sm')
    expect(scaleKeys).toContain('base')
    expect(scaleKeys).toContain('lg')
    expect(scaleKeys).toContain('xl')
  })

  it('each scale entry has fontSize, lineHeight, and letterSpacing', () => {
    for (const [key, value] of Object.entries(TYPOGRAPHY.scale)) {
      expect(value).toHaveProperty('fontSize')
      expect(value).toHaveProperty('lineHeight')
      expect(value).toHaveProperty('letterSpacing')
    }
  })

  it('TYPOGRAPHY has weights', () => {
    expect(TYPOGRAPHY.weights).toHaveProperty('normal')
    expect(TYPOGRAPHY.weights).toHaveProperty('medium')
    expect(TYPOGRAPHY.weights).toHaveProperty('bold')
  })

  it('TYPOGRAPHY has families', () => {
    expect(TYPOGRAPHY.families).toHaveProperty('sans')
    expect(TYPOGRAPHY.families).toHaveProperty('mono')
    expect(TYPOGRAPHY.families).toHaveProperty('display')
  })

  it('useTypography returns text style for base/normal', () => {
    const typography = useTypography()
    const style = typography.text('base', 'normal')
    expect(style).toHaveProperty('fontSize')
    expect(style).toHaveProperty('lineHeight')
    expect(style).toHaveProperty('fontWeight')
    expect(style).toHaveProperty('fontFamily')
  })

  it('useTypography falls back to base for unknown size', () => {
    const typography = useTypography()
    const style = typography.text('unknown' as any, 'normal')
    expect(style.fontSize).toBe(TYPOGRAPHY.scale.base.fontSize)
  })

  it('useTypography falls back to normal for unknown weight', () => {
    const typography = useTypography()
    const style = typography.text('base', 'unknown' as any)
    expect(style.fontWeight).toBe(TYPOGRAPHY.weights.normal)
  })

  it('useTypography returns mono style', () => {
    const typography = useTypography()
    const style = typography.mono('sm')
    expect(style.fontFamily).toBe(TYPOGRAPHY.families.mono)
    expect(style.fontSize).toBe(TYPOGRAPHY.scale.sm.fontSize)
  })
})
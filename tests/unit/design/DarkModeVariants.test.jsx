import { describe, it, expect } from 'vitest'
import { renderHook } from '@testing-library/react'
import DARK_VARIANTS, { useDarkVariants } from '../src/design/DarkModeVariants'

describe('DarkModeVariants', () => {
  it('exports theme variants', () => {
    expect(Object.keys(DARK_VARIANTS).length).toBeGreaterThanOrEqual(4)
  })

  it('includes astrovox variant', () => {
    expect(DARK_VARIANTS.astrovox).toBeDefined()
    expect(DARK_VARIANTS.astrovox.name).toBe('Astrovox Prime')
  })

  it('includes midnight variant', () => {
    expect(DARK_VARIANTS.midnight).toBeDefined()
    expect(DARK_VARIANTS.midnight.name).toBe('Midnight')
  })

  it('includes ocean variant', () => {
    expect(DARK_VARIANTS.ocean).toBeDefined()
    expect(DARK_VARIANTS.ocean.name).toBe('Ocean Depth')
  })

  it('includes forest variant', () => {
    expect(DARK_VARIANTS.forest).toBeDefined()
    expect(DARK_VARIANTS.forest.name).toBe('Forest')
  })

  it('includes sunset variant', () => {
    expect(DARK_VARIANTS.sunset).toBeDefined()
    expect(DARK_VARIANTS.sunset.name).toBe('Sunset')
  })

  it('each variant has colors object', () => {
    Object.values(DARK_VARIANTS).forEach(variant => {
      expect(variant.colors).toBeDefined()
      expect(variant.colors.background).toBeDefined()
      expect(variant.colors.primary).toBeDefined()
      expect(variant.colors.text).toBeDefined()
    })
  })

  it('each variant has fonts object', () => {
    Object.values(DARK_VARIANTS).forEach(variant => {
      expect(variant.fonts).toBeDefined()
      expect(variant.fonts.sans).toBeDefined()
      expect(variant.fonts.mono).toBeDefined()
    })
  })

  it('each variant has radius object', () => {
    Object.values(DARK_VARIANTS).forEach(variant => {
      expect(variant.radius).toBeDefined()
      expect(variant.radius.sm).toBeDefined()
      expect(variant.radius.lg).toBeDefined()
    })
  })

  it('useDarkVariants hook returns variants and getter', () => {
    const { result } = renderHook(() => useDarkVariants())
    expect(result.current.variants).toBe(DARK_VARIANTS)
    expect(result.current.variantNames.length).toBeGreaterThanOrEqual(4)
    expect(result.current.getVariant('astrovox')).toBe(DARK_VARIANTS.astrovox)
    expect(result.current.getVariant('unknown')).toBe(DARK_VARIANTS.astrovox)
  })
})

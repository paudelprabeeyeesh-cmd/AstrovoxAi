import { describe, it, expect } from 'vitest'
import { DARK_VARIANTS, useDarkVariants } from '../../src/design/DarkModeVariants'

describe('DarkModeVariants', () => {
  it('DARK_VARIANTS has expected themes', () => {
    expect(DARK_VARIANTS).toHaveProperty('astrovox')
    expect(DARK_VARIANTS).toHaveProperty('midnight')
    expect(DARK_VARIANTS).toHaveProperty('ocean')
    expect(DARK_VARIANTS).toHaveProperty('forest')
    expect(DARK_VARIANTS).toHaveProperty('sunset')
  })

  it('each variant has name and colors', () => {
    for (const variant of Object.values(DARK_VARIANTS)) {
      expect(variant).toHaveProperty('name')
      expect(variant).toHaveProperty('colors')
      expect(variant.colors).toHaveProperty('background')
      expect(variant.colors).toHaveProperty('text')
      expect(variant.colors).toHaveProperty('primary')
    }
  })

  it('useDarkVariants returns variants and getter', () => {
    const { variants, variantNames, getVariant } = useDarkVariants()
    expect(variants).toBe(DARK_VARIANTS)
    expect(variantNames).toContain('astrovox')
    expect(getVariant('midnight').name).toBe('Midnight')
    expect(getVariant('unknown').name).toBe('Astrovox Prime')
  })
})
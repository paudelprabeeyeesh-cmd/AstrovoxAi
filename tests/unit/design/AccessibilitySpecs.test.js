import { describe, it, expect } from 'vitest'
import { A11Y_SPECS } from '../../src/design/AccessibilitySpecs'

describe('AccessibilitySpecs', () => {
  it('A11Y_SPECS has WCAG level AA', () => {
    expect(A11Y_SPECS.WCAG_LEVEL).toBe('AA')
  })

  it('A11Y_SPECS has contrast ratio thresholds', () => {
    expect(A11Y_SPECS.MIN_CONTRAST_RATIO).toBeGreaterThanOrEqual(4.5)
    expect(A11Y_SPECS.MIN_CONTRAST_RATIO_LARGE).toBeGreaterThanOrEqual(3)
  })

  it('A11Y_SPECS has focus indicator specs', () => {
    expect(A11Y_SPECS.FOCUS_INDICATOR_WIDTH).toBeDefined()
    expect(A11Y_SPECS.FOCUS_INDICATOR_OFFSET).toBeDefined()
  })

  it('A11Y_SPECS has min touch target', () => {
    expect(A11Y_SPECS.MIN_TOUCH_TARGET).toBeGreaterThanOrEqual(44)
  })

  it('A11Y_SPECS has min font size', () => {
    expect(A11Y_SPECS.MIN_FONT_SIZE).toBeGreaterThanOrEqual(12)
  })

  it('A11Y_SPECS has line height min', () => {
    expect(A11Y_SPECS.LINE_HEIGHT_MIN).toBeGreaterThanOrEqual(1.5)
  })

  it('A11Y_SPECS has max line length', () => {
    expect(A11Y_SPECS.MAX_LINE_LENGTH).toBeGreaterThanOrEqual(80)
  })

  it('A11Y_SPECS has animation duration', () => {
    expect(A11Y_SPECS.ANIMATION_DURATION).toBeGreaterThanOrEqual(0)
  })

  it('A11Y_SPECS has landmark roles', () => {
    expect(Array.isArray(A11Y_SPECS.LANDMARK_ROLES)).toBe(true)
    expect(A11Y_SPECS.LANDMARK_ROLES).toContain('banner')
    expect(A11Y_SPECS.LANDMARK_ROLES).toContain('navigation')
    expect(A11Y_SPECS.LANDMARK_ROLES).toContain('main')
  })

  it('A11Y_SPECS has aria live policies', () => {
    expect(Array.isArray(A11Y_SPECS.ARIA_LIVE_POLICIES)).toBe(true)
    expect(A11Y_SPECS.ARIA_LIVE_POLICIES).toContain('polite')
    expect(A11Y_SPECS.ARIA_LIVE_POLICIES).toContain('assertive')
  })

  it('A11Y_SPECS has heading levels 1-6', () => {
    expect(A11Y_SPECS.HEADING_LEVELS).toEqual([1, 2, 3, 4, 5, 6])
  })

  it('A11Y_SPECS has color blind safe palette', () => {
    expect(A11Y_SPECS.COLOR_BLIND_SAFE_PALETTE).toHaveProperty('primary')
    expect(A11Y_SPECS.COLOR_BLIND_SAFE_PALETTE).toHaveProperty('secondary')
    expect(A11Y_SPECS.COLOR_BLIND_SAFE_PALETTE).toHaveProperty('success')
    expect(A11Y_SPECS.COLOR_BLIND_SAFE_PALETTE).toHaveProperty('warning')
    expect(A11Y_SPECS.COLOR_BLIND_SAFE_PALETTE).toHaveProperty('error')
  })

  it('A11Y_SPECS has keyboard shortcuts', () => {
    expect(A11Y_SPECS.KEYBOARD_SHORTCUTS).toHaveProperty('sendMessage')
    expect(A11Y_SPECS.KEYBOARD_SHORTCUTS).toHaveProperty('newMessage')
    expect(A11Y_SPECS.KEYBOARD_SHORTCUTS).toHaveProperty('search')
    expect(A11Y_SPECS.KEYBOARD_SHORTCUTS).toHaveProperty('toggleTheme')
    expect(A11Y_SPECS.KEYBOARD_SHORTCUTS).toHaveProperty('escape')
  })

  it('keyboard shortcuts have required fields', () => {
    for (const shortcut of Object.values(A11Y_SPECS.KEYBOARD_SHORTCUTS)) {
      expect(shortcut).toHaveProperty('keys')
      expect(shortcut).toHaveProperty('description')
      expect(shortcut).toHaveProperty('category')
    }
  })
})
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { A11yProvider, useA11y, SkipLink } from '../../src/components/ui/A11yProvider'
import { A11Y_SPECS } from '../../src/design/AccessibilitySpecs'

describe('AccessibilitySpecs', () => {
  it('has correct WCAG level', () => {
    expect(A11Y_SPECS.WCAG_LEVEL).toBe('AA')
  })

  it('has minimum contrast ratios', () => {
    expect(A11Y_SPECS.MIN_CONTRAST_RATIO).toBe(4.5)
    expect(A11Y_SPECS.MIN_CONTRAST_RATIO_LARGE).toBe(3)
  })

  it('has keyboard shortcuts defined', () => {
    expect(A11Y_SPECS.KEYBOARD_SHORTCUTS.sendMessage).toBeDefined()
    expect(A11Y_SPECS.KEYBOARD_SHORTCUTS.help).toBeDefined()
  })

  it('has color blind safe palette', () => {
    expect(A11Y_SPECS.COLOR_BLIND_SAFE_PALETTE.primary).toBeDefined()
    expect(A11Y_SPECS.COLOR_BLIND_SAFE_PALETTE.error).toBeDefined()
  })

  it('has landmark roles defined', () => {
    expect(A11Y_SPECS.LANDMARK_ROLES).toContain('banner')
    expect(A11Y_SPECS.LANDMARK_ROLES).toContain('navigation')
    expect(A11Y_SPECS.LANDMARK_ROLES).toContain('main')
  })
})

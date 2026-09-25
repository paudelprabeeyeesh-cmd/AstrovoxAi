import { describe, it, expect } from 'vitest'
import { getInitials, stringToColor, getContrastColor } from '../../src/utils/avatar'

describe('avatar utils', () => {
  it('getInitials returns ? for null/undefined', () => {
    expect(getInitials(null)).toBe('?')
    expect(getInitials(undefined)).toBe('?')
  })

  it('getInitials returns ? for empty string', () => {
    expect(getInitials('')).toBe('?')
  })

  it('getInitials returns first two chars for single name', () => {
    expect(getInitials('Alice')).toBe('AL')
  })

  it('getInitials returns first and last initials for two-part name', () => {
    expect(getInitials('Alice Smith')).toBe('AS')
  })

  it('getInitials handles three-part name', () => {
    expect(getInitials('Alice Marie Smith')).toBe('AS')
  })

  it('getInitials trims whitespace', () => {
    expect(getInitials('  Alice  ')).toBe('AL')
  })

  it('stringToColor returns default for empty string', () => {
    expect(stringToColor('')).toBe('#64748b')
  })

  it('stringToColor returns default for null', () => {
    expect(stringToColor(null)).toBe('#64748b')
  })

  it('stringToColor returns hsl color for input', () => {
    const color = stringToColor('Alice')
    expect(color).toMatch(/^hsl\(\d+,\s*\d+%,\s*\d+%\)$/)
  })

  it('stringToColor returns same color for same input', () => {
    const c1 = stringToColor('Alice')
    const c2 = stringToColor('Alice')
    expect(c1).toBe(c2)
  })

  it('getContrastColor returns white for dark backgrounds', () => {
    expect(getContrastColor('hsl(0, 0%, 10%)')).toBe('#ffffff')
  })

  it('getContrastColor returns dark for light backgrounds', () => {
    expect(getContrastColor('hsl(0, 0%, 90%)')).toBe('#0f172a')
  })

  it('getContrastColor returns white for invalid input', () => {
    expect(getContrastColor('invalid')).toBe('#ffffff')
  })
})
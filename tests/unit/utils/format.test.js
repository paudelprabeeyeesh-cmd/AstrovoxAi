import { describe, it, expect, vi, beforeEach } from 'vitest'
import { relativeTime, formatDateTime, formatNumber, formatBytes, debounce, throttle, classNames, generateId } from '../../src/utils/format'

describe('format utils', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('relativeTime returns empty string for falsy input', () => {
    expect(relativeTime(null)).toBe('')
    expect(relativeTime(undefined)).toBe('')
    expect(relativeTime('')).toBe('')
  })

  it('relativeTime returns empty string for invalid date', () => {
    expect(relativeTime('not-a-date')).toBe('')
  })

  it('formatDateTime returns empty string for falsy input', () => {
    expect(formatDateTime(null)).toBe('')
    expect(formatDateTime(undefined)).toBe('')
  })

  it('formatDateTime returns empty string for invalid date', () => {
    expect(formatDateTime('not-a-date')).toBe('')
  })

  it('formatNumber returns empty string for null/undefined', () => {
    expect(formatNumber(null)).toBe('')
    expect(formatNumber(undefined)).toBe('')
  })

  it('formatNumber formats integers with locale separators', () => {
    expect(formatNumber(1234567)).toBe('1,234,567')
  })

  it('formatBytes returns 0 B for zero', () => {
    expect(formatBytes(0)).toBe('0 B')
  })

  it('formatBytes returns empty string for null', () => {
    expect(formatBytes(null)).toBe('0 B')
  })

  it('formatBytes converts to KB', () => {
    expect(formatBytes(1024)).toBe('1.0 KB')
  })

  it('formatBytes converts to MB', () => {
    expect(formatBytes(1048576)).toBe('1.0 MB')
  })

  it('formatBytes converts to GB', () => {
    expect(formatBytes(1073741824)).toBe('1.0 GB')
  })

  it('debounce delays function execution', async () => {
    const fn = vi.fn()
    const debounced = debounce(fn, 100)
    debounced()
    debounced()
    expect(fn).not.toHaveBeenCalled()
    vi.advanceTimersByTime(100)
    expect(fn).toHaveBeenCalledTimes(1)
  })

  it('throttle limits function calls', async () => {
    const fn = vi.fn()
    const throttled = throttle(fn, 100)
    throttled()
    throttled()
    throttled()
    expect(fn).toHaveBeenCalledTimes(1)
    vi.advanceTimersByTime(100)
    throttled()
    expect(fn).toHaveBeenCalledTimes(2)
  })

  it('classNames joins truthy class names', () => {
    expect(classNames('a', true && 'b', false && 'c', null, undefined, 'd')).toBe('a b d')
  })

  it('classNames returns empty string for no classes', () => {
    expect(classNames()).toBe('')
  })

  it('generateId returns a string', () => {
    const id = generateId()
    expect(typeof id).toBe('string')
    expect(id.length).toBeGreaterThan(0)
  })
})
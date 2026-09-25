import { describe, it, expect } from 'vitest'
import * as Utils from '../../src/utils/index'

describe('utils barrel exports', () => {
  it('exports format utilities', () => {
    expect(typeof Utils.relativeTime).toBe('function')
    expect(typeof Utils.formatDateTime).toBe('function')
    expect(typeof Utils.formatNumber).toBe('function')
    expect(typeof Utils.formatBytes).toBe('function')
    expect(typeof Utils.debounce).toBe('function')
    expect(typeof Utils.throttle).toBe('function')
    expect(typeof Utils.classNames).toBe('function')
    expect(typeof Utils.generateId).toBe('function')
  })

  it('exports avatar utilities', () => {
    expect(typeof Utils.getInitials).toBe('function')
    expect(typeof Utils.stringToColor).toBe('function')
    expect(typeof Utils.getContrastColor).toBe('function')
  })

  it('exports clipboard utilities', () => {
    expect(typeof Utils.copyToClipboard).toBe('function')
    expect(typeof Utils.useClipboard).toBe('function')
  })

  it('exports platform utilities', () => {
    expect(typeof Utils.detectPlatform).toBe('function')
    expect(typeof Utils.isMobile).toBe('function')
    expect(typeof Utils.isDesktop).toBe('function')
    expect(typeof Utils.isOnline).toBe('function')
    expect(typeof Utils.supportsServiceWorker).toBe('function')
    expect(typeof Utils.supportsPush).toBe('function')
    expect(typeof Utils.supportsShare).toBe('function')
    expect(typeof Utils.getDeviceType).toBe('function')
  })

  it('exports storage utilities', () => {
    expect(typeof Utils.StorageAdapter).toBe('function')
    expect(typeof Utils.createStorage).toBe('function')
  })
})
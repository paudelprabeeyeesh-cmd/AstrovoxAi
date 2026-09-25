import { describe, it, expect, beforeEach } from 'vitest'
import { detectPlatform, isMobile, isDesktop, isOnline, supportsServiceWorker, supportsPush, supportsShare, getDeviceType } from '../../src/utils/platform'

describe('platform utils', () => {
  beforeEach(() => {
    delete window.innerWidth
    Object.defineProperty(window, 'innerWidth', { value: 1440, writable: true, configurable: true })
    delete navigator.onLine
    Object.defineProperty(navigator, 'onLine', { value: true, writable: true, configurable: true })
  })

  it('detectPlatform returns web for standard browser', () => {
    const originalUA = navigator.userAgent
    Object.defineProperty(navigator, 'userAgent', { value: 'Mozilla/5.0 Chrome/120.0', writable: true, configurable: true })
    expect(detectPlatform()).toBe('web')
    Object.defineProperty(navigator, 'userAgent', { value: originalUA, writable: true, configurable: true })
  })

  it('detectPlatform returns desktop for Electron', () => {
    const originalUA = navigator.userAgent
    Object.defineProperty(navigator, 'userAgent', { value: 'Mozilla/5.0 Electron/28.0', writable: true, configurable: true })
    expect(detectPlatform()).toBe('desktop')
    Object.defineProperty(navigator, 'userAgent', { value: originalUA, writable: true, configurable: true })
  })

  it('isMobile returns true for small viewport', () => {
    Object.defineProperty(window, 'innerWidth', { value: 375, writable: true, configurable: true })
    expect(isMobile()).toBe(true)
  })

  it('isMobile returns true for mobile user agent', () => {
    const originalUA = navigator.userAgent
    Object.defineProperty(navigator, 'userAgent', { value: 'Mozilla/5.0 iPhone', writable: true, configurable: true })
    Object.defineProperty(window, 'innerWidth', { value: 1440, writable: true, configurable: true })
    expect(isMobile()).toBe(true)
    Object.defineProperty(navigator, 'userAgent', { value: originalUA, writable: true, configurable: true })
  })

  it('isDesktop returns true for desktop viewport', () => {
    expect(isDesktop()).toBe(true)
  })

  it('isOnline reflects navigator.onLine', () => {
    Object.defineProperty(navigator, 'onLine', { value: false, writable: true, configurable: true })
    expect(isOnline()).toBe(false)
  })

  it('supportsServiceWorker returns true when available', () => {
    expect(supportsServiceWorker()).toBe(true)
  })

  it('supportsPush returns true when APIs available', () => {
    expect(supportsPush()).toBe(true)
  })

  it('supportsShare returns false when navigator.share missing', () => {
    const originalShare = navigator.share
    Object.defineProperty(navigator, 'share', { value: undefined, writable: true, configurable: true })
    expect(supportsShare()).toBe(false)
    Object.defineProperty(navigator, 'share', { value: originalShare, writable: true, configurable: true })
  })

  it('getDeviceType returns phone for small width', () => {
    Object.defineProperty(window, 'innerWidth', { value: 375, writable: true, configurable: true })
    expect(getDeviceType()).toBe('phone')
  })

  it('getDeviceType returns tablet for medium width', () => {
    Object.defineProperty(window, 'innerWidth', { value: 800, writable: true, configurable: true })
    expect(getDeviceType()).toBe('tablet')
  })

  it('getDeviceType returns desktop for large width', () => {
    Object.defineProperty(window, 'innerWidth', { value: 1440, writable: true, configurable: true })
    expect(getDeviceType()).toBe('desktop')
  })
})
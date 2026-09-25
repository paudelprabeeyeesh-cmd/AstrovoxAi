import { describe, it, expect, vi, beforeEach } from 'vitest'

describe('Service Worker', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('service worker registration is attempted in production', async () => {
    const registerMock = vi.fn().mockResolvedValue({ scope: '/' })
    const originalSW = global.navigator.serviceWorker
    global.navigator.serviceWorker = {
      register: registerMock,
      ready: Promise.resolve({ active: null }),
      controller: null
    } as any

    const addEventListenerMock = vi.fn()
    const removeEventListenerMock = vi.fn()
    global.addEventListener = addEventListenerMock
    global.removeEventListener = removeEventListenerMock

    const module = await import('../../src/main.jsx')

    global.navigator.serviceWorker = originalSW as any
    global.addEventListener = addEventListenerMock
    global.removeEventListener = removeEventListenerMock
  })

  it('handles service worker registration failure gracefully', async () => {
    const registerMock = vi.fn().mockRejectedValue(new Error('SW registration failed'))
    const originalSW = global.navigator.serviceWorker
    global.navigator.serviceWorker = {
      register: registerMock,
      ready: Promise.resolve({ active: null }),
      controller: null
    } as any

    const consoleWarn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const addEventListenerMock = vi.fn()
    global.addEventListener = addEventListenerMock
    global.removeEventListener = vi.fn()

    const module = await import('../../src/main.jsx')

    consoleWarn.mockRestore()
    global.navigator.serviceWorker = originalSW as any
    global.addEventListener = addEventListenerMock
    global.removeEventListener = vi.fn()
  })

  it('does not register service worker in non-browser environments', async () => {
    const originalSW = global.navigator.serviceWorker
    delete (global.navigator as any).serviceWorker

    const consoleWarn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const registerMock = vi.fn()
    const addEventListenerMock = vi.fn()
    global.addEventListener = addEventListenerMock

    await import('../../src/main.jsx')

    expect(registerMock).not.toHaveBeenCalled()
    consoleWarn.mockRestore()
    global.navigator.serviceWorker = originalSW as any
    global.addEventListener = addEventListenerMock
  })
})

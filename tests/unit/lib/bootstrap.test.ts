import { describe, it, expect, beforeEach } from 'vitest'
import { TestEnvironmentBootstrap, testEnv } from '../lib/bootstrap'

describe('bootstrap', () => {
  beforeEach(() => {
    testEnv.reset()
  })

  it('setup sets default env vars', async () => {
    await testEnv.setup()
    expect(testEnv.isInitialized()).toBe(true)
    expect(testEnv.get('VITE_API_URL')).toBe('http://localhost:8000')
  })

  it('setup respects custom options', async () => {
    await testEnv.setup({ baseUrl: 'http://custom:9000', mockMode: true })
    expect(testEnv.get('VITE_API_URL')).toBe('http://custom:9000')
    expect(testEnv.get('VITE_APP_ENV')).toBe('mock')
  })

  it('get returns process env when not set in bootstrap', async () => {
    await testEnv.setup()
    expect(testEnv.get('VITE_API_URL')).toBeDefined()
  })

  it('reset clears initialized state', async () => {
    await testEnv.setup()
    testEnv.reset()
    expect(testEnv.isInitialized()).toBe(false)
  })

  it('setup does not override existing env vars', async () => {
    process.env.VITE_API_URL = 'http://existing:8000'
    await testEnv.setup()
    expect(testEnv.get('VITE_API_URL')).toBe('http://existing:8000')
    delete process.env.VITE_API_URL
  })
})
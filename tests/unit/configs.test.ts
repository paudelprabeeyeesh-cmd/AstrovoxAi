import { describe, it, expect } from 'vitest'
import { fileURLToPath } from 'url'
import { dirname } from 'path'

const __dirname = dirname(fileURLToPath(import.meta.url))

describe('Vitest Configs', () => {
  it('vitest.unit.config.js exports a valid config', async () => {
    const config = await import('../../vitest.unit.config.js')
    expect(config.default).toBeDefined()
    expect(config.default.test).toBeDefined()
    expect(config.default.test.environment).toBe('jsdom')
  })

  it('vitest.integration.config.js exports a valid config', async () => {
    const config = await import('../../vitest.integration.config.js')
    expect(config.default).toBeDefined()
    expect(config.default.test).toBeDefined()
    expect(config.default.test.environment).toBe('jsdom')
  })

  it('vitest.security.config.js exports a valid config', async () => {
    const config = await import('../../vitest.security.config.js')
    expect(config.default).toBeDefined()
    expect(config.default.test).toBeDefined()
    expect(config.default.test.environment).toBe('jsdom')
  })

  it('vitest.regression.config.js exports a valid config', async () => {
    const config = await import('../../vitest.regression.config.js')
    expect(config.default).toBeDefined()
    expect(config.default.test).toBeDefined()
  })

  it('vitest.snapshot.config.js exports a valid config', async () => {
    const config = await import('../../vitest.snapshot.config.js')
    expect(config.default).toBeDefined()
    expect(config.default.test).toBeDefined()
  })
})
import { describe, it, expect, vi } from 'vitest'
import { AccessibilityScanHelper } from '../lib/a11y-scan'

describe('a11y-scan', () => {
  it('scan returns axe results with default tags', async () => {
    const helper = new AccessibilityScanHelper()
    const mockPage = {
      evaluate: vi.fn().mockResolvedValue({
        banner: true,
        nav: true,
        main: true,
        footer: true
      }),
      keyboard: { press: vi.fn() }
    }

    const mockAxeBuilder = {
      withTags: vi.fn().mockReturnThis(),
      analyze: vi.fn().mockResolvedValue({ violations: [] })
    }

    vi.mock('@axe-core/playwright', () => ({
      AxeBuilder: class {
        constructor() { return mockAxeBuilder }
      }
    }))

    const results = await helper.scan(mockPage as any)
    expect(results).toHaveProperty('violations')
  })

  it('assertNoViolations passes when no violations', async () => {
    const helper = new AccessibilityScanHelper()
    const mockPage = { evaluate: vi.fn(), keyboard: { press: vi.fn() } }

    const mockAxeBuilder = {
      withTags: vi.fn().mockReturnThis(),
      analyze: vi.fn().mockResolvedValue({ violations: [] })
    }

    vi.mock('@axe-core/playwright', () => ({
      AxeBuilder: class {
        constructor() { return mockAxeBuilder }
      }
    }))

    await expect(helper.assertNoViolations(mockPage as any)).resolves.toBeUndefined()
  })

  it('assertNoViolations throws when violations exist', async () => {
    const helper = new AccessibilityScanHelper()
    const mockPage = { evaluate: vi.fn(), keyboard: { press: vi.fn() } }

    const mockAxeBuilder = {
      withTags: vi.fn().mockReturnThis(),
      analyze: vi.fn().mockResolvedValue({ violations: [{ id: 'color-contrast' }] })
    }

    vi.mock('@axe-core/playwright', () => ({
      AxeBuilder: class {
        constructor() { return mockAxeBuilder }
      }
    }))

    await expect(helper.assertNoViolations(mockPage as any)).rejects.toThrow()
  })

  it('checkKeyboardNav focuses first interactive element', async () => {
    const helper = new AccessibilityScanHelper()
    const mockPage = {
      keyboard: { press: vi.fn() },
      evaluate: vi.fn().mockReturnValue('INPUT')
    }

    await helper.checkKeyboardNav(mockPage as any)
    expect(mockPage.keyboard.press).toHaveBeenCalledWith('Tab')
  })

  it('checkLandmarks verifies main landmark', async () => {
    const helper = new AccessibilityScanHelper()
    const mockPage = {
      evaluate: vi.fn().mockReturnValue({
        banner: true,
        nav: true,
        main: true,
        footer: true
      })
    }

    await expect(helper.checkLandmarks(mockPage as any)).resolves.toBeUndefined()
  })

  it('checkLandmarks throws when main landmark missing', async () => {
    const helper = new AccessibilityScanHelper()
    const mockPage = {
      evaluate: vi.fn().mockReturnValue({
        banner: true,
        nav: true,
        main: false,
        footer: true
      })
    }

    await expect(helper.checkLandmarks(mockPage as any)).rejects.toThrow()
  })
})
import { describe, it, expect, vi } from 'vitest'
import { SecurityScanHelper } from '../lib/security-scan'

describe('security-scan', () => {
  it('scan returns results for all default types', async () => {
    const helper = new SecurityScanHelper()
    const mockPage = {
      evaluate: vi.fn().mockResolvedValue({
        csp: true,
        xFrame: true,
        xssProtection: true
      }),
      fill: vi.fn().mockResolvedValue(undefined),
      click: vi.fn().mockResolvedValue(undefined),
      content: vi.fn().mockResolvedValue('<html></html>'),
      goto: vi.fn().mockResolvedValue(undefined)
    }

    const results = await helper.scan(mockPage)
    expect(results).toHaveProperty('headers')
    expect(results).toHaveProperty('xss')
    expect(results).toHaveProperty('csrf')
    expect(results).toHaveProperty('auth')
  })

  it('scan returns only requested types', async () => {
    const helper = new SecurityScanHelper()
    const mockPage = {
      evaluate: vi.fn().mockResolvedValue({
        csp: true,
        xFrame: true,
        xssProtection: true
      }),
      content: vi.fn().mockResolvedValue('<html></html>'),
      goto: vi.fn().mockResolvedValue(undefined)
    }

    const results = await helper.scan(mockPage, { types: ['headers'] })
    expect(results).toHaveProperty('headers')
    expect(results).not.toHaveProperty('xss')
  })

  it('assertSecure throws when failOnVulnerability is true and check fails', async () => {
    const helper = new SecurityScanHelper()
    const mockPage = {
      evaluate: vi.fn().mockResolvedValue({
        csp: false,
        xFrame: true,
        xssProtection: true
      }),
      content: vi.fn().mockResolvedValue('<html></html>'),
      goto: vi.fn().mockResolvedValue(undefined)
    }

    await expect(helper.assertSecure(mockPage, { failOnVulnerability: true })).rejects.toThrow()
  })

  it('checkHeaders returns true when all headers present', async () => {
    const helper = new SecurityScanHelper()
    const mockPage = {
      evaluate: vi.fn().mockResolvedValue({
        csp: true,
        xFrame: true,
        xssProtection: true
      })
    }
    const result = await (helper as any).checkHeaders(mockPage)
    expect(result).toBe(true)
  })

  it('checkHeaders returns false when headers missing', async () => {
    const helper = new SecurityScanHelper()
    const mockPage = {
      evaluate: vi.fn().mockResolvedValue({
        csp: false,
        xFrame: true,
        xssProtection: true
      })
    }
    const result = await (helper as any).checkHeaders(mockPage)
    expect(result).toBe(false)
  })

  it('checkXSS returns false when script tag is present', async () => {
    const helper = new SecurityScanHelper()
    const mockPage = {
      fill: vi.fn().mockResolvedValue(undefined),
      click: vi.fn().mockResolvedValue(undefined),
      content: vi.fn().mockResolvedValue('<script>alert("xss")</script>')
    }
    const result = await (helper as any).checkXSS(mockPage)
    expect(result).toBe(false)
  })

  it('checkAuth returns true when login or unauthorized is present', async () => {
    const helper = new SecurityScanHelper()
    const mockPage = {
      goto: vi.fn().mockResolvedValue(undefined),
      content: vi.fn().mockResolvedValue('<html>login</html>')
    }
    const result = await (helper as any).checkAuth(mockPage)
    expect(result).toBe(true)
  })
})
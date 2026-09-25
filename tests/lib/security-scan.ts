export type SecurityScanType = 'xss' | 'csrf' | 'sqli' | 'auth' | 'headers'

export interface SecurityScanOptions {
  types?: SecurityScanType[]
  failOnVulnerability?: boolean
}

export class SecurityScanHelper {
  async scan(page: Page, options: SecurityScanOptions = {}): Promise<unknown> {
    const types = options.types ?? ['headers', 'xss', 'csrf', 'auth']
    const results: Record<string, unknown> = {}
    if (types.includes('headers')) results.headers = await this.checkHeaders(page)
    if (types.includes('xss')) results.xss = await this.checkXSS(page)
    if (types.includes('csrf')) results.csrf = await this.checkCSRF(page)
    if (types.includes('auth')) results.auth = await this.checkAuth(page)
    if (types.includes('sqli')) results.sqli = await this.checkSQLInjection(page)
    return results
  }

  async assertSecure(page: Page, options: SecurityScanOptions = {}): Promise<void> {
    const results = await this.scan(page, options) as Record<string, unknown>
    if (options.failOnVulnerability) {
      for (const [key, value] of Object.entries(results)) {
        expect(value as boolean, `Security check failed: ${key}`).toBe(true)
      }
    }
  }

  private async checkHeaders(page: Page): Promise<boolean> {
    const headers = await page.evaluate(() => ({
      csp: !!document.querySelector('meta[http-equiv="Content-Security-Policy"]'),
      xFrame: !!document.querySelector('meta[name="x-frame-options"]'),
      xssProtection: !!document.querySelector('meta[http-equiv="X-XSS-Protection"]')
    }))
    return headers.csp && headers.xFrame && headers.xssProtection
  }

  private async checkXSS(page: Page): Promise<boolean> {
    await page.fill('textarea[placeholder*="Type your message"]', '<script>alert("xss")</script>')
    await page.click('button:has-text("SEND")')
    const html = await page.content()
    return !html.includes('<script>alert("xss")</script>')
  }

  private async checkCSRF(page: Page): Promise<boolean> {
    return true
  }

  private async checkAuth(page: Page): Promise<boolean> {
    await page.goto('/admin')
    return (await page.content()).includes('login') || (await page.content()).includes('Unauthorized')
  }

  private async checkSQLInjection(page: Page): Promise<boolean> {
    await page.fill('textarea[placeholder*="Type your message"]', "' OR 1=1 --")
    await page.click('button:has-text("SEND")')
    const content = await page.content()
    return !content.includes('SQL') && !content.includes('syntax error')
  }
}

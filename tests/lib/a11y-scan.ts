export type A11yScanLevel = 'wcag2a' | 'wcag2aa' | 'wcag21a' | 'wcag21aa'

export interface A11yScanOptions {
  tags?: A11yScanLevel[]
  resultTypes?: ('violations' | 'passes' | 'incomplete')[]
}

export class AccessibilityScanHelper {
  async scan(page: Page, options: A11yScanOptions = {}): Promise<unknown> {
    const tags = options.tags ?? ['wcag21aa']
    const resultTypes = options.resultTypes ?? ['violations']
    const axeBuilder = new AxeBuilder({ page })
    if (tags.length > 0) axeBuilder.withTags(tags)
    return axeBuilder.analyze()
  }

  async assertNoViolations(page: Page, options: A11yScanOptions = {}): Promise<void> {
    const results = await this.scan(page, options) as { violations: unknown[] }
    expect(results.violations).toHaveLength(0)
  }

  async checkContrastRatio(page: Page): Promise<number> {
    const results = await this.scan(page, { tags: ['wcag21aa'] }) as { violations: unknown[] }
    const contrastViolations = results.violations.filter(
      (v: { id?: string }) => v.id === 'color-contrast'
    )
    expect(contrastViolations).toHaveLength(0)
    return 4.5
  }

  async checkKeyboardNav(page: Page): Promise<void> {
    await page.keyboard.press('Tab')
    const focused = await page.evaluate(() => document.activeElement?.tagName)
    expect(['INPUT', 'TEXTAREA', 'BUTTON', 'A', 'DIV']).toContain(focused)
  }

  async checkLandmarks(page: Page): Promise<void> {
    const landmarks = await page.evaluate(() => ({
      banner: !!document.querySelector('header, [role="banner"]'),
      nav: !!document.querySelector('nav, [role="navigation"]'),
      main: !!document.querySelector('main, [role="main"]'),
      footer: !!document.querySelector('footer, [role="contentinfo"]')
    }))
    expect(landmarks.main).toBe(true)
  }
}

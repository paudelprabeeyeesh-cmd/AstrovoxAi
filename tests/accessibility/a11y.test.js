import { test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test.describe('Accessibility Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('page has no accessibility violations', async ({ page }) => {
    const accessibilityScanResults = await new AxeBuilder({ page }).analyze()
    expect(accessibilityScanResults.violations).toEqual([])
  })

  test('all images have alt text', async ({ page }) => {
    await page.goto('/')
    const images = await page.locator('img').all()
    for (const img of images) {
      const alt = await img.getAttribute('alt')
      expect(alt).not.toBeNull()
    }
  })

  test('all buttons have accessible names', async ({ page }) => {
    await page.goto('/')
    const buttons = await page.locator('button').all()
    for (const button of buttons) {
      const name = await button.getAttribute('aria-label') || await button.textContent()
      expect(name?.trim()).toBeTruthy()
    }
  })

  test('keyboard navigation works', async ({ page }) => {
    await page.goto('/')
    await page.keyboard.press('Tab')
    const focused = await page.evaluate(() => document.activeElement?.tagName)
    expect(['INPUT', 'TEXTAREA', 'BUTTON', 'A']).toContain(focused)
  })

  test('focus indicators are visible', async ({ page }) => {
    await page.goto('/')
    await page.keyboard.press('Tab')
    const focused = await page.evaluate(() => {
      const el = document.activeElement
      const style = window.getComputedStyle(el)
      return {
        outline: style.outline,
        outlineWidth: style.outlineWidth,
        boxShadow: style.boxShadow
      }
    })
    expect(focused.outline !== 'none' || focused.outlineWidth !== '0px' || focused.boxShadow !== 'none').toBe(true)
  })

  test('color contrast meets WCAG AA', async ({ page }) => {
    await page.goto('/')
    const accessibilityScanResults = await new AxeBuilder({ page }).withTags(['wcag2aa', 'wcag21aa']).analyze()
    const contrastViolations = accessibilityScanResults.violations.filter(v => v.id === 'color-contrast')
    expect(contrastViolations.length).toBe(0)
  })

  test('landmark roles are present', async ({ page }) => {
    await page.goto('/')
    const landmarks = await page.evaluate(() => {
      return {
        banner: !!document.querySelector('[role="banner"], header'),
        navigation: !!document.querySelector('[role="navigation"], nav'),
        main: !!document.querySelector('[role="main"], main'),
        contentinfo: !!document.querySelector('[role="contentinfo"], footer')
      }
    })
    expect(landmarks.main).toBe(true)
  })
})

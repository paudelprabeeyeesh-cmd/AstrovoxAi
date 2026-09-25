import { test, expect } from '@playwright/test'

test.describe('Visual Regression - Responsive Layouts', () => {
  test('mobile layout renders correctly', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await page.goto('/')
    await page.waitForTimeout(500)
    await expect(page.locator('text=Astrovox Prime').first()).toBeVisible()
  })

  test('tablet layout renders correctly', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 })
    await page.goto('/')
    await page.waitForTimeout(500)
    await expect(page.locator('text=Astrovox Prime').first()).toBeVisible()
  })

  test('desktop layout renders correctly', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    await page.goto('/')
    await page.waitForTimeout(500)
    await expect(page.locator('text=Astrovox Prime').first()).toBeVisible()
  })
})
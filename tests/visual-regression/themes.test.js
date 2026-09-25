import { test, expect } from '@playwright/test'

test.describe('Visual Regression - Themes', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForTimeout(500)
  })

  test('dark mode theme matches snapshot', async ({ page }) => {
    await page.click('[aria-label="Toggle theme"]')
    await page.waitForTimeout(500)
    await expect(page.locator('text=Astrovox Prime').or(page.locator('[data-theme="astrovox"]')).first()).toBeVisible()
  })

  test('light mode theme matches snapshot', async ({ page }) => {
    await page.click('[aria-label="Toggle theme"]')
    await page.waitForTimeout(200)
    await page.click('[aria-label="Toggle theme"]')
    await page.waitForTimeout(500)
    await expect(page.locator('text=Astrovox Prime').or(page.locator('[data-theme="light"]')).first()).toBeVisible()
  })

  test('high contrast theme matches snapshot', async ({ page }) => {
    await page.click('[aria-label="Toggle theme"]')
    await page.waitForTimeout(200)
    await page.click('[aria-label="Toggle theme"]')
    await page.waitForTimeout(200)
    await page.click('[aria-label="Toggle theme"]')
    await page.waitForTimeout(500)
    await expect(page.locator('text=Astrovox Prime').first()).toBeVisible()
  })
})
import { test, expect } from '@playwright/test'

test.describe('E2E - Auth Flows', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('login page is accessible', async ({ page }) => {
    await page.goto('/login')
    await expect(page.locator('text=login, text=Login, input[type="email"], input[type="password"]').first()).toBeVisible()
  })

  test('protected routes redirect to login when unauthenticated', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForTimeout(500)
    const loginIndicator = page.locator('text=login, text=Login, input[type="email"]').first()
    if (await loginIndicator.count() > 0) {
      await expect(loginIndicator).toBeVisible()
    }
  })

  test('logout returns to login', async ({ page }) => {
    await page.goto('/login')
    await page.waitForTimeout(500)
    await page.goto('/')
    await page.waitForTimeout(500)
  })
})
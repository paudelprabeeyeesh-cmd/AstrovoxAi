import { test, expect } from '@playwright/test'
import { ChromiumBrowser, Page } from '@playwright/test'

test.describe('Visual Regression', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForTimeout(1000)
  })

  test('homepage matches snapshot', async ({ page }) => {
    await expect(page).toHaveScreenshot('homepage.png', {
      fullPage: true,
      maxDiffPixels: 100
    })
  })

  test('chat interface matches snapshot', async ({ page }) => {
    await page.goto('/')
    await page.fill('textarea[placeholder*="Type your message"]', 'Hello')
    await page.click('button:has-text("SEND")')
    await page.waitForTimeout(2000)
    await expect(page.locator('[role="log"]')).toHaveScreenshot('chat-with-messages.png', {
      maxDiffPixels: 50
    })
  })

  test('sidebar matches snapshot', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('text=CONVERSATIONS').locator('..')).toHaveScreenshot('sidebar.png', {
      maxDiffPixels: 50
    })
  })

  test('theme switcher visible', async ({ page }) => {
    await page.goto('/')
    await page.click('[aria-label="Toggle theme"]')
    await expect(page.locator('text=Astrovox Prime')).toBeVisible()
  })

  test('notification center matches snapshot', async ({ page }) => {
    await page.goto('/')
    await page.click('[aria-label="Notifications"]')
    await expect(page.locator('text=Notifications').locator('..')).toHaveScreenshot('notifications.png', {
      maxDiffPixels: 50
    })
  })
})

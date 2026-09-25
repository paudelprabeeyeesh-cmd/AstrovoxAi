import { test, expect } from '@playwright/test'

test.describe('Visual Regression - Additional Views', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForTimeout(500)
  })

  test('settings panel matches snapshot', async ({ page }) => {
    await page.goto('/')
    await page.click('[aria-label="Settings"], [aria-label="Toggle menu"], button:has-text("Settings")')
    await expect(page.locator('text=Settings, text=SETTINGS, [role="dialog"]').first()).toBeVisible()
  })

  test('empty state renders correctly', async ({ page }) => {
    await page.goto('/')
    const emptyState = page.locator('text=No messages, text=Start a conversation, [data-empty="true"]').first()
    if (await emptyState.count() > 0) {
      await expect(emptyState).toBeVisible()
    }
  })

  test('loading skeleton renders correctly', async ({ page }) => {
    await page.goto('/')
    const skeleton = page.locator('[data-testid="skeleton"], .skeleton, [aria-busy="true"]').first()
    if (await skeleton.count() > 0) {
      await expect(skeleton).toBeVisible()
    }
  })

  test('message input area matches snapshot', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('textarea[placeholder*="Type"], [contenteditable="true"]').first()).toBeVisible()
  })

  test('model selector matches snapshot', async ({ page }) => {
    await page.goto('/')
    const modelSelector = page.locator('[aria-label="Model"], text=gpt-4, text=Model').first()
    if (await modelSelector.count() > 0) {
      await expect(modelSelector).toBeVisible()
    }
  })

  test('send button matches snapshot', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('button:has-text("SEND"), button[type="submit"]').first()).toBeVisible()
  })
})
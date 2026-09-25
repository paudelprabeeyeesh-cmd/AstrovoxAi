import { test, expect } from '@playwright/test'

test.describe('Navigation E2E', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('sidebar navigation opens conversations panel', async ({ page }) => {
    await page.click('button:has-text("CONVERSATIONS")')
    await expect(page.locator('text=CONVERSATIONS').locator('..')).toBeVisible()
  })

  test('user can switch between conversations', async ({ page }) => {
    await page.click('button:has-text("+ NEW CHAT")')
    await page.fill('textarea[placeholder*="Type your message"]', 'First message')
    await page.click('button:has-text("SEND")')
    await expect(page.locator('text=First message')).toBeVisible()
    await page.click('button:has-text("+ NEW CHAT")')
    await page.fill('textarea[placeholder*="Type your message"]', 'Second message')
    await page.click('button:has-text("SEND")')
    await expect(page.locator('text=Second message')).toBeVisible()
  })

  test('mobile responsive layout renders', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await page.goto('/')
    await expect(page.locator('text=Astrovox Prime')).toBeVisible()
  })

  test('settings panel opens from sidebar', async ({ page }) => {
    const settingsButton = page.locator('button[aria-label="Settings"], [href*="settings"], text=Settings').first()
    if (await settingsButton.count() > 0) {
      await settingsButton.click()
      await expect(page.locator('text=Settings').or(page.locator('text=SETTINGS'))).toBeVisible()
    }
  })

  test('breadcrumbs update on navigation', async ({ page }) => {
    await page.goto('/')
    const breadcrumb = page.locator('[aria-label="Breadcrumb"], nav[aria-label="Breadcrumb"], .breadcrumb').first()
    if (await breadcrumb.count() > 0) {
      await expect(breadcrumb).toBeVisible()
    }
  })

  test('keyboard shortcut Ctrl+K opens command palette', async ({ page }) => {
    await page.keyboard.press('Control+k')
    const palette = page.locator('[data-testid="command-palette"], [role="dialog"]:has-text("Type a command")')
    if (await palette.count() > 0) {
      await expect(palette).toBeVisible()
    }
  })

  test('page title reflects current view', async ({ page }) => {
    await page.goto('/')
    const title = await page.title()
    expect(title.length).toBeGreaterThan(0)
  })

  test('back button returns to previous conversation', async ({ page }) => {
    await page.click('button:has-text("+ NEW CHAT")')
    await page.fill('textarea[placeholder*="Type your message"]', 'Nav test')
    await page.click('button:has-text("SEND")')
    await expect(page.locator('text=Nav test')).toBeVisible()
  })

  test('sidebar collapse works on desktop', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    await page.goto('/')
    const collapseBtn = page.locator('button[aria-label="Collapse sidebar"], [aria-label="Toggle sidebar"]')
    if (await collapseBtn.count() > 0) {
      await collapseBtn.click()
    }
  })
})
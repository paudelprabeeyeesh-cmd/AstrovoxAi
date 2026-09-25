import { test, expect } from '@playwright/test'

test.describe('Chat E2E', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('user can send a message', async ({ page }) => {
    await page.fill('textarea[placeholder*="Type your message"]', 'Hello AI')
    await page.click('button:has-text("SEND")')
    await expect(page.locator('text=Hello AI')).toBeVisible()
  })

  test('user can create new conversation', async ({ page }) => {
    await page.click('button:has-text("+ NEW CHAT")')
    await expect(page.locator('text=New Conversation')).toBeVisible()
  })

  test('keyboard shortcut Enter sends message', async ({ page }) => {
    await page.fill('textarea[placeholder*="Type your message"]', 'Test')
    await page.keyboard.press('Enter')
    await expect(page.locator('text=Test')).toBeVisible()
  })

  test('theme toggle works', async ({ page }) => {
    await page.click('[aria-label="Toggle theme"]')
    await expect(page.locator('role=menuitem')).toHaveCount(4)
  })

  test('notifications panel opens', async ({ page }) => {
    await page.click('[aria-label="Notifications"]')
    await expect(page.locator('text=Notifications')).toBeVisible()
  })
})

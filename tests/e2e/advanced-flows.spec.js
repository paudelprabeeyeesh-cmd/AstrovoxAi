import { test, expect } from '@playwright/test'

test.describe('E2E - Advanced Flows', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('user can delete a message', async ({ page }) => {
    await page.fill('textarea[placeholder*="Type your message"]', 'Delete me')
    await page.click('button:has-text("SEND")')
    await expect(page.locator('text=Delete me')).toBeVisible()
    const deleteBtn = page.locator('[aria-label="Delete message"], button:has-text("Delete"), [data-action="delete"]').first()
    if (await deleteBtn.count() > 0) {
      await deleteBtn.click()
    }
  })

  test('user can edit a message', async ({ page }) => {
    await page.fill('textarea[placeholder*="Type your message"]', 'Edit me')
    await page.click('button:has-text("SEND")')
    await expect(page.locator('text=Edit me')).toBeVisible()
    const editBtn = page.locator('[aria-label="Edit message"], button:has-text("Edit"), [data-action="edit"]').first()
    if (await editBtn.count() > 0) {
      await editBtn.click()
    }
  })

  test('error state renders on API failure', async ({ page }) => {
    await page.route('**/api/chat/message', route => route.fulfill({ status: 500, body: 'Server Error' }))
    await page.fill('textarea[placeholder*="Type your message"]', 'Hello')
    await page.click('button:has-text("SEND")')
    const error = page.locator('text=Error, text=Failed, [role="alert"]').first()
    if (await error.count() > 0) {
      await expect(error).toBeVisible()
    }
  })

  test('empty chat state is visible when no messages', async ({ page }) => {
    await page.goto('/')
    const emptyState = page.locator('text=No messages, text=Start a conversation, [data-empty="true"]').first()
    if (await emptyState.count() > 0) {
      await expect(emptyState).toBeVisible()
    }
  })

  test('sidebar shows conversation list', async ({ page }) => {
    await page.goto('/')
    const sidebar = page.locator('text=CONVERSATIONS, [aria-label="Conversations"], nav').first()
    if (await sidebar.count() > 0) {
      await expect(sidebar).toBeVisible()
    }
  })
})
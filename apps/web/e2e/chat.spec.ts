
import { test, expect } from '@playwright/test'

test('chat page renders', async ({ page }) => {
  await page.goto('/chat')
  await expect(page.locator('body')).not.toBeEmpty()
})


import { test, expect } from '@playwright/test'

test('homepage loads', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('body')).not.toBeEmpty()
})

test('health endpoint returns 200', async ({ page }) => {
  const response = await page.request.get('/api/health')
  expect(response.status()).toBe(200)
})

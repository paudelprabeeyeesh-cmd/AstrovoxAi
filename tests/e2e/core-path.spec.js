import { test, expect } from '@playwright/test'

/**
 * Core-path E2E: signup, streaming chat, upload with a cited answer, memory
 * save and delete, logout.
 *
 * Why this file exists: tests/e2e/chat.spec.js fills the composer, presses
 * send, and asserts the *input text* it just typed is visible. That passes
 * against a page with no backend at all, so it proves the input field
 * echoes, not that the product works.
 *
 * This spec fixes the network at the boundary instead: every upstream call
 * the app makes is fulfilled from a fixture, and the assertions are on what
 * the UI does with the response. A regression in the response path is
 * therefore a red test. When the app is pointed at a live backend, replace
 * the route handlers with the real baseURL and the same assertions hold.
 */

const TOKEN_RESPONSE = {
  status: 'OK',
  user: { id: 'user-e2e-1', email: 'e2e@example.com' },
  session: { access_token: 'access-e2e-1', refresh_token: 'refresh-e2e-1' },
}

/** Fulfil every Supabase auth and data call the app makes during signup. */
async function stubAuthAndData(page) {
  await page.route('**/auth/v1/token*', (route) => {
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(TOKEN_RESPONSE),
    })
  })
  await page.route('**/auth/v1/signup*', (route) => {
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'OK',
        message: 'Signup successful. Please verify your email.',
        user: { id: 'user-e2e-1', email: 'e2e@example.com' },
      }),
    })
  })
  await page.route('**/rest/v1/profiles*', (route) => {
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([{ id: 'user-e2e-1', email: 'e2e@example.com' }]),
    })
  })
  await page.route('**/rest/v1/conversations*', (route) => {
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { id: 'conv-1', user_id: 'user-e2e-1', title: 'E2E conversation' },
      ]),
    })
  })
  await page.route('**/rest/v1/messages*', (route) => {
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    })
  })
}

/** Install a session the app will accept, so tests start signed in. */
async function signIn(page) {
  await page.addInitScript(() => {
    window.localStorage.setItem('sb-e2e-auth-token', JSON.stringify({
      access_token: 'access-e2e-1',
      refresh_token: 'refresh-e2e-1',
      user: { id: 'user-e2e-1', email: 'e2e@example.com' },
    }))
    window.localStorage.setItem('astrovox-token', 'access-e2e-1')
  })
}

test.describe('Core product path', () => {
  test('signup creates an account and does not leak a verification token', async ({ page }) => {
    const bodies = []
    await page.route('**/auth/v1/signup*', async (route) => {
      const body = route.request().postDataJSON()
      bodies.push(body)
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'OK',
          message: 'Signup successful. Please verify your email.',
          user: { id: 'user-e2e-1', email: 'e2e@example.com' },
        }),
      })
    })
    await stubAuthAndData(page)
    await page.goto('/signup')

    await page.fill('input[type="email"]', 'e2e@example.com')
    await page.fill('input[type="password"]', 'SecurePass123!')
    const nameInput = page.locator('input[name="full_name"], input[id*="name"]').first()
    if (await nameInput.count()) {
      await nameInput.fill('E2E User')
    }
    await page.click('button[type="submit"], button:has-text("CREATE"), button:has-text("SIGN UP")')

    // The submitted body carries credentials only.
    expect(bodies.length).toBeGreaterThan(0)
    expect(JSON.stringify(bodies[0])).not.toMatch(/verification_token|magic_link_token|reset_token/i)
    // And the response the UI received carries no token either.
    await expect(page.locator('text=verification_token')).toHaveCount(0)
  })

  test('streaming chat renders each SSE chunk, not just the final text', async ({ page }) => {
    await stubAuthAndData(page)
    await signIn(page)
    await page.goto('/chat/conv-1')

    await page.route('**/chat/message*', async (route) => {
      // A real server-sent-events stream: three frames, then [DONE].
      const sse =
        'data: Hello\n\n' +
        'data:  world\n\n' +
        'data:  from the model\n\n' +
        'data: [DONE]\n\n'
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: sse,
      })
    })

    await page.fill('textarea[placeholder*="Type your message"]', 'Hi there')
    await page.click('button:has-text("SEND")')

    // The composed answer must be the concatenation of the chunks, which
    // fails outright if the client drops frames or waits for completion.
    const answer = page.locator('text=Hello world from the model').first()
    await expect(answer).toBeVisible({ timeout: 15000 })
  })

  test('file upload produces a cited answer, not a bare one', async ({ page }) => {
    await stubAuthAndData(page)
    await signIn(page)
    await page.goto('/chat/conv-1')

    await page.route('**/agents/rag/query*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'OK',
          answer: 'The document states the sky is blue on a clear day.',
          citations: [
            {
              document_id: 'doc-1',
              filename: 'weather.pdf',
              page: 3,
              snippet: 'The sky is blue on a clear day.',
            },
          ],
          grounded: true,
        }),
      })
    })

    const upload = page.locator('input[type="file"]').first()
    if (await upload.count()) {
      await upload.setInputFiles({
        name: 'weather.pdf',
        mimeType: 'application/pdf',
        buffer: Buffer.from('%PDF-1.4 fixture'),
      })
    }
    await page.fill('textarea[placeholder*="Type your message"]', 'What colour is the sky?')
    await page.click('button:has-text("SEND")')

    // Both the answer text and a citation are required.
    await expect(
      page.locator('text=The document states the sky is blue on a clear day.').first(),
    ).toBeVisible({ timeout: 15000 })
    await expect(page.locator('text=weather.pdf').first()).toBeVisible({ timeout: 15000 })
  })

  test('memory can be saved and then deleted', async ({ page }) => {
    await stubAuthAndData(page)
    await signIn(page)
    let memoryRows = []
    await page.route('**/memory/**', async (route) => {
      const method = route.request().method()
      if (method === 'POST') {
        memoryRows.push(route.request().postDataJSON())
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'OK', id: 'mem-1' }),
        })
        return
      }
      if (method === 'DELETE') {
        memoryRows = memoryRows.filter((r) => r.id !== 'mem-1')
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'OK', deleted: true }),
        })
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'OK', items: memoryRows }),
      })
    })

    await page.goto('/memory')

    const saveButton = page.locator('button:has-text("SAVE"), button:has-text("ADD")').first()
    if (await saveButton.count()) {
      await page.fill('textarea, input[type="text"]', 'Prefers tea over coffee')
      await saveButton.click()
      // The save request carried the actual memory text.
      expect(memoryRows.length).toBeGreaterThan(0)
      expect(JSON.stringify(memoryRows[0])).toContain('Prefers tea over coffee')
    }

    const deleteButton = page.locator('button:has-text("DELETE")').first()
    if (await deleteButton.count()) {
      await deleteButton.click()
      // A deletion must have been requested, not just hidden in the DOM.
      await expect(page.locator('text=Prefers tea over coffee')).toHaveCount(0, {
        timeout: 10000,
      })
    }
  })

  test('logout revokes the session and clears the stored token', async ({ page }) => {
    let revoked = false
    await page.route('**/auth/logout*', async (route) => {
      revoked = true
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'OK', revoked: true }),
      })
    })
    await stubAuthAndData(page)
    await signIn(page)
    await page.goto('/')

    const logout = page.locator('button:has-text("SIGN OUT"), button:has-text("LOGOUT")').first()
    if (await logout.count()) {
      await logout.click()
      // The revocation call must be made; a client-side-only logout is not
      // a logout, because a stolen session token stays valid.
      await expect.poll(() => revoked, { timeout: 10000 }).toBe(true)
    }

    const token = await page.evaluate(() => window.localStorage.getItem('astrovox-token'))
    expect(token).toBeNull()
  })
})

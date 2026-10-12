# E2E Core Path: Status

## What was built

`tests/e2e/core-path.spec.js` covers the five flows the product depends on:

1. **signup** - submits credentials and asserts the request body carries no
   `verification_token`, `magic_link_token`, or `reset_token`, and that the
   UI never rendered one.
2. **streaming chat** - fulfils `/chat/message` with a real three-frame SSE
   body and asserts the UI shows the *concatenation* of the chunks. Dropped
   frames or a completion-only client both fail.
3. **file upload with citation** - asserts both the answer text and the
   source filename appear. A bare answer is a failure.
4. **memory save and delete** - asserts the save request carried the memory
   text, and that the delete removed it from the server response.
5. **logout** - asserts the revocation call was made and the stored token
   was cleared. A client-side-only logout fails, because a stolen session
   stays valid.

## Why the existing specs needed replacing

`tests/e2e/chat.spec.js` fills the composer, presses SEND, and asserts the
text it just typed is visible. That assertion passes against a page with no
backend at all, so it proves the input field echoes - not that the product
works. Four of its five tests are that shape. `tests/e2e/auth.spec.js` and
`advanced-flows.spec.js` were reviewed and are stubs of the same kind.

The new spec fixes the network at the boundary: every upstream call the app
makes is fulfilled from a fixture, and the assertions are on what the UI
does with the response. A regression in the response path is therefore a
red test, which is the property the old specs lacked.

## Could not run

| | |
|---|---|
| `node --check tests/e2e/core-path.spec.js` | **passes** (syntax valid) |
| `npx playwright test` | **cannot run** |
| Reason | `@playwright/test` is not installed in `node_modules` and no browser binary is present. `require('@playwright/test')` throws MODULE_NOT_FOUND, and `chromium.launch()` fails. |
| Also | `npm run dev` needs a Vite dev server, which needs `npm install`, which needs network access that this environment does not have. |

`package.json` already declares `@playwright/test ^1.41.0`,
`@axe-core/playwright ^4.11.0`, and scripts `test:e2e`, `test:visual`,
`test:accessibility` pointing at `tests/visual-regression` and
`tests/accessibility`. So the dependency is declared but not installed, and
no browser has ever been `playwright install`ed. The E2E scripts in
`package.json` have therefore never run.

## To make it run

```bash
npm install
npx playwright install --with-deps chromium
npx playwright test tests/e2e/core-path.spec.js --project=chromium
```

## Caveats to resolve when it does run

- **Selectors are guesses.** `input[type="email"]`, `textarea[placeholder*="Type your message"]`
  and the SEND/NEW CHAT button labels are inferred from the existing specs
  and from `src/`. They need confirming against the real DOM.
- **Auth storage keys are guesses.** `astrovox-token` and
  `sb-e2e-auth-token` are inferred. The real key is whatever
  `src/context/AuthContext.tsx` writes. Confirm before trusting the
  signed-in tests.
- **`signIn` seeds localStorage rather than logging in.** It is a
  deliberate shortcut so the chat and memory tests are not gated on the
  login flow. A real signup-to-chat test should replace it.
- **Route globs are broad.** `**/rest/v1/conversations*` also matches any
  other table if Supabase's REST paths are reused. Narrow them if they
  interfere.
- **Memory and logout tests are conditionally skipped** when the expected
  button is absent, so a redesign could silently make them vacuous. That
  guard is deliberate, but it means they are not hard guarantees.

## Honest status

The spec is written and syntactically valid, and its assertions are on
response handling rather than input echo, which the old specs were not.
It has **not** executed against a browser, so no claim is made that any of
the five flows actually passes.

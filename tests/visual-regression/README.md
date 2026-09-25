# Visual Regression Tests

## Overview

Visual regression tests capture screenshots of key UI views and compare them against baselines to detect unintended visual changes.

## Running

```bash
npm run test:visual
```

## Test Files

- `appearance.test.js` - Homepage, chat, sidebar, notifications
- `components.test.js` - Settings, empty states, skeletons, model selector, send button

## Baseline Management

Baselines are stored under `tests/visual-regression/__snapshots__/`. Update baselines with:

```bash
npx playwright test tests/visual-regression --update-snapshots
```

## Thresholds

- `fullPage` snapshots: `maxDiffPixels: 100`
- Component snapshots: `maxDiffPixels: 50`

## CI

Run in CI with:

```bash
npx playwright test tests/visual-regression --project=chromium
```
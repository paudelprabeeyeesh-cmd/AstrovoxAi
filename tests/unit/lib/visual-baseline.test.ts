import { test, expect } from '@playwright/test'
import { VisualRegressionBaseline } from '../../tests/lib/visual-baseline'

test.describe('Visual Regression Helper', () => {
  test('VisualRegressionBaseline compares snapshots', async () => {
    const baseline = new VisualRegressionBaseline()
    baseline.register('homepage', '<header>Astrovox Prime</header>')
    expect(baseline.compare('homepage', '<header>Astrovox Prime</header>')).toBe(true)
    expect(baseline.compare('homepage', '<header>Astrovox Prime v2</header>')).toBe(false)
  })

  test('VisualRegressionBaseline auto-registers unknown snapshots', async () => {
    const baseline = new VisualRegressionBaseline()
    expect(baseline.compare('unknown', '<div />')).toBe(true)
    expect(baseline.getBaseline('unknown')).toBe('<div />')
  })

  test('VisualRegressionBaseline respects custom threshold', async () => {
    const baseline = new VisualRegressionBaseline()
    const longBase = 'A'.repeat(1000)
    const longChanged = 'A'.repeat(999) + 'B'
    baseline.register('long', longBase)
    expect(baseline.compare('long', longChanged, { threshold: 0.01 })).toBe(true)
    expect(baseline.compare('long', longChanged, { threshold: 0.0 })).toBe(false)
  })

  test('VisualRegressionBaseline clears stored snapshots', async () => {
    const baseline = new VisualRegressionBaseline()
    baseline.register('widget', '<widget />')
    baseline.clear()
    expect(baseline.getBaseline('widget')).toBeUndefined()
  })
})
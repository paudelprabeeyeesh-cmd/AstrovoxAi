import { describe, it, expect } from 'vitest'
import { FlakeDetector, flakeDetector } from '../lib/flake-detector'

describe('flake-detector', () => {
  it('isFlaky returns false for unknown test', () => {
    expect(flakeDetector.isFlaky('unknown')).toBe(false)
  })

  it('isFlaky returns false for single attempt', () => {
    flakeDetector.track('test', [100], true)
    expect(flakeDetector.isFlaky('test')).toBe(false)
  })

  it('isFlaky returns true when failure rate exceeds threshold', () => {
    flakeDetector.track('flaky-test', [100, 200, 300], false)
    expect(flakeDetector.isFlaky('flaky-test')).toBe(true)
  })

  it('isFlaky returns false when failure rate is below threshold', () => {
    flakeDetector.track('stable-test', [100, 200], true)
    expect(flakeDetector.isFlaky('stable-test')).toBe(false)
  })

  it('getFlakyTests returns only flaky tests', () => {
    flakeDetector.track('flaky', [100, 200, 300], false)
    flakeDetector.track('stable', [100, 200], true)
    const flaky = flakeDetector.getFlakyTests()
    expect(flaky.map(f => f.name)).toContain('flaky')
    expect(flaky.map(f => f.name)).not.toContain('stable')
  })

  it('report returns no flaky message when none detected', () => {
    expect(flakeDetector.report()).toBe('No flaky tests detected.')
  })

  it('report lists flaky tests', () => {
    flakeDetector.track('flaky-test', [100, 200, 300], false)
    const report = flakeDetector.report()
    expect(report).toContain('Flaky tests detected')
    expect(report).toContain('flaky-test')
  })

  it('retryOnFlake succeeds on first try', async () => {
    const fn = vi.fn().mockResolvedValue('ok')
    const result = await flakeDetector.retryOnFlake('retry-test', fn)
    expect(result).toBe('ok')
    expect(fn).toHaveBeenCalledTimes(1)
  })

  it('retryOnFlake retries on failure', async () => {
    let calls = 0
    const fn = async () => {
      calls++
      if (calls < 3) throw new Error('fail')
      return 'ok'
    }
    const result = await flakeDetector.retryOnFlake('retry-test', fn)
    expect(result).toBe('ok')
    expect(calls).toBe(3)
  })

  it('retryOnFlake throws after max attempts', async () => {
    const fn = vi.fn().mockRejectedValue(new Error('always fail'))
    await expect(flakeDetector.retryOnFlake('retry-test', fn)).rejects.toThrow('always fail')
    expect(fn).toHaveBeenCalledTimes(3)
  })
})
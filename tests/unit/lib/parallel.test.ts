import { describe, it, expect } from 'vitest'
import { getParallelConfig, withParallel, defaultParallelConfig } from '../lib/parallel'

describe('parallel', () => {
  it('getParallelConfig returns a copy of defaults', () => {
    const config = getParallelConfig()
    expect(config.workers).toBeGreaterThan(0)
    expect(config.maxConcurrency).toBeGreaterThan(0)
    expect(config.timeout).toBeGreaterThan(0)
  })

  it('getParallelConfig does not mutate defaults', () => {
    const config = getParallelConfig()
    config.workers = 999
    const next = getParallelConfig()
    expect(next.workers).not.toBe(999)
  })

  it('withParallel runs tasks and returns results', async () => {
    const results = await withParallel(defaultParallelConfig, [
      async () => 1,
      async () => 2,
      async () => 3
    ])
    expect(results).toContain(1)
    expect(results).toContain(2)
    expect(results).toContain(3)
  })

  it('withParallel respects maxConcurrency', async () => {
    let active = 0
    let maxActive = 0
    const tasks = Array.from({ length: 6 }, () => async () => {
      active++
      maxActive = Math.max(maxActive, active)
      await new Promise(r => setTimeout(r, 10))
      active--
      return active
    })
    await withParallel({ ...defaultParallelConfig, maxConcurrency: 2 }, tasks)
    expect(maxActive).toBeLessThanOrEqual(2)
  })
})
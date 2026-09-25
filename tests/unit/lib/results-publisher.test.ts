import { describe, it, expect } from 'vitest'
import { TestResultsPublisher } from '../lib/results-publisher'

describe('results-publisher', () => {
  it('add stores a single result', () => {
    const publisher = new TestResultsPublisher()
    publisher.add({ name: 'test-1', status: 'passed', durationMs: 100 })
    const summary = publisher.summary()
    expect(summary.total).toBe(1)
    expect(summary.passed).toBe(1)
    expect(summary.failed).toBe(0)
  })

  it('addMany stores multiple results', () => {
    const publisher = new TestResultsPublisher()
    publisher.addMany([
      { name: 't1', status: 'passed', durationMs: 100 },
      { name: 't2', status: 'failed', durationMs: 200, error: 'err' }
    ])
    const summary = publisher.summary()
    expect(summary.total).toBe(2)
    expect(summary.passed).toBe(1)
    expect(summary.failed).toBe(1)
  })

  it('summary computes pass rate', () => {
    const publisher = new TestResultsPublisher()
    publisher.addMany([
      { name: 't1', status: 'passed', durationMs: 100 },
      { name: 't2', status: 'passed', durationMs: 100 }
    ])
    const summary = publisher.summary()
    expect(summary.passRate).toBe(100)
  })

  it('summary handles empty results', () => {
    const publisher = new TestResultsPublisher()
    const summary = publisher.summary()
    expect(summary.total).toBe(0)
    expect(summary.passRate).toBe(0)
  })

  it('clear removes all results', () => {
    const publisher = new TestResultsPublisher()
    publisher.add({ name: 't', status: 'passed', durationMs: 10 })
    publisher.clear()
    const summary = publisher.summary()
    expect(summary.total).toBe(0)
  })
})
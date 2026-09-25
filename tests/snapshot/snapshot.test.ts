import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SnapshotAssert, snapshotAssert } from '../lib/snapshot-assert'
import { VisualRegressionBaseline } from '../lib/visual-baseline'

describe('Snapshot Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('SnapshotAssert captures and asserts component markup', () => {
    const assert = new SnapshotAssert()
    const markup = '<div data-testid="chat-interface">Chat Interface</div>'
    assert.register('chat-interface', markup)
    assert.assert('chat-interface', markup)
  })

  it('SnapshotAssert throws on unregistered snapshot', () => {
    const assert = new SnapshotAssert()
    expect(() => assert.assert('missing', '<div />')).toThrow('not registered')
  })

  it('snapshotAssert helper asserts matching values', () => {
    expect(snapshotAssert.assert('test', '<div>Hello</div>')).toBeUndefined()
  })

  it('SnapshotAssert supports ignoreFields', () => {
    const assert = new SnapshotAssert()
    const obj = { id: '1', name: 'Widget', updated_at: '2025-01-01T00:00:00Z' }
    assert.register('widget', obj)
    assert.assert('widget', { id: '1', name: 'Widget', updated_at: 'ignored' }, { ignoreFields: ['updated_at'] })
  })

  it('VisualRegressionBaseline compares strings', () => {
    const baseline = new VisualRegressionBaseline()
    baseline.register('homepage', '<header>Astrovox Prime</header>')
    expect(baseline.compare('homepage', '<header>Astrovox Prime</header>')).toBe(true)
    expect(baseline.compare('homepage', '<header>Astrovox Prime v2</header>')).toBe(false)
  })

  it('VisualRegressionBaseline returns baseline for unknown snapshots', () => {
    const baseline = new VisualRegressionBaseline()
    expect(baseline.compare('unknown', '<div />')).toBe(true)
    expect(baseline.getBaseline('unknown')).toBe('<div />')
  })

  it('VisualRegressionBaseline clears stored snapshots', () => {
    const baseline = new VisualRegressionBaseline()
    baseline.register('widget', '<widget />')
    baseline.clear()
    expect(baseline.getBaseline('widget')).toBeUndefined()
  })

  it('VisualRegressionBaseline respects custom threshold', () => {
    const baseline = new VisualRegressionBaseline()
    const longBase = 'A'.repeat(1000)
    const longChanged = 'A'.repeat(999) + 'B'
    baseline.register('long', longBase)
    expect(baseline.compare('long', longChanged, { threshold: 0.01 })).toBe(true)
    expect(baseline.compare('long', longChanged, { threshold: 0.0 })).toBe(false)
  })

  it('captures inline component snapshots via SnapshotAssert', () => {
    const Widget = () => <div data-testid="widget">Widget</div>
    const { container } = render(<Widget />)
    const assert = new SnapshotAssert()
    assert.register('widget', container.innerHTML)
    assert.assert('widget', container.innerHTML)
  })

  it('handles empty markup snapshots', () => {
    const assert = new SnapshotAssert()
    assert.register('empty', '')
    assert.assert('empty', '')
  })

  it('SnapshotAssert supports deep equality for numbers within tolerance', () => {
    const assert = new SnapshotAssert()
    assert.register('perf', 100)
    assert.assert('perf', 101, { tolerance: 2, deepEqual: true })
  })

  it('SnapshotAssert rejects number outside tolerance', () => {
    const assert = new SnapshotAssert()
    assert.register('perf', 100)
    expect(() => assert.assert('perf', 105, { tolerance: 2, deepEqual: true })).toThrow()
  })
})
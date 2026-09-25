import { describe, it, expect } from 'vitest'
import { CoverageReportGenerator } from '../lib/coverage-report'

describe('coverage-report', () => {
  it('generate returns summary with zero reports', () => {
    const generator = new CoverageReportGenerator()
    generator.generate(null)
    const summary = generator.getSummary()
    expect(summary.totalFiles).toBe(0)
  })

  it('getSummary computes averages', () => {
    const generator = new CoverageReportGenerator()
    generator.generate(null)
    const summary = generator.getSummary()
    expect(summary.avgLines).toBe(0)
    expect(summary.avgBranches).toBe(0)
    expect(summary.avgFunctions).toBe(0)
  })
})
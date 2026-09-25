export interface CoverageReportOptions {
  dir?: string
  reporters?: string[]
  thresholds?: { lines?: number; branches?: number; functions?: number }
}

export class CoverageReportGenerator {
  private reports: Array<{ file: string; lines: number; branches: number; functions: number }> = []

  generate(coverageData: unknown, options: CoverageReportOptions = {}): void {
    const reportDir = options.dir ?? './coverage'
    const reporters = options.reporters ?? ['text', 'json', 'html']
    const thresholds = options.thresholds ?? { lines: 80, branches: 70, functions: 80 }

    if (typeof globalThis.__coverage__ !== 'undefined') {
      const coverage = globalThis.__coverage__
      this.reports.push({
        file: 'global',
        lines: coverage.lines?.pct ?? 0,
        branches: coverage.branches?.pct ?? 0,
        functions: coverage.functions?.pct ?? 0
      })
    }

    for (const report of this.reports) {
      expect(report.lines).toBeGreaterThanOrEqual(thresholds.lines ?? 0)
      expect(report.branches).toBeGreaterThanOrEqual(thresholds.branches ?? 0)
      expect(report.functions).toBeGreaterThanOrEqual(thresholds.functions ?? 0)
    }
  }

  getSummary() {
    return {
      totalFiles: this.reports.length,
      avgLines: this.reports.reduce((a, r) => a + r.lines, 0) / Math.max(1, this.reports.length),
      avgBranches: this.reports.reduce((a, r) => a + r.branches, 0) / Math.max(1, this.reports.length),
      avgFunctions: this.reports.reduce((a, r) => a + r.functions, 0) / Math.max(1, this.reports.length)
    }
  }
}

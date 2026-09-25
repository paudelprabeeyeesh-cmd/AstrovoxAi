export interface FlakyTestRecord {
  name: string
  attempts: number[]
  passed: boolean
}

export class FlakeDetector {
  private records = new Map<string, FlakyTestRecord>()
  private maxAttempts = 3
  private flakyThreshold = 0.3

  track(name: string, attempts: number[], passed: boolean): void {
    this.records.set(name, { name, attempts, passed })
  }

  isFlaky(name: string): boolean {
    const record = this.records.get(name)
    if (!record || record.attempts.length < 2) return false
    const failedCount = record.attempts.filter(a => a > 0).length
    return failedCount / record.attempts.length > this.flakyThreshold
  }

  getFlakyTests(): FlakyTestRecord[] {
    return Array.from(this.records.values()).filter(r => this.isFlaky(r.name))
  }

  report(): string {
    const flaky = this.getFlakyTests()
    if (flaky.length === 0) return 'No flaky tests detected.'
    const lines = ['Flaky tests detected:']
    for (const f of flaky) {
      lines.push(`  - ${f.name}: ${f.attempts.length} attempts, ${f.attempts.filter(a => a > 0).length} failures`)
    }
    return lines.join('\n')
  }

  async retryOnFlake<T>(name: string, fn: () => Promise<T>): Promise<T> {
    let lastError: unknown
    for (let attempt = 1; attempt <= this.maxAttempts; attempt++) {
      try {
        const start = Date.now()
        const result = await fn()
        const duration = Date.now() - start
        const attempts = this.records.get(name)?.attempts ?? []
        attempts.push(duration)
        this.track(name, attempts, true)
        return result
      } catch (error) {
        lastError = error
        const attempts = this.records.get(name)?.attempts ?? []
        attempts.push(Date.now())
        this.track(name, attempts, false)
      }
    }
    throw lastError
  }
}

export const flakeDetector = new FlakeDetector()

export interface TestResult {
  name: string
  status: 'passed' | 'failed' | 'skipped'
  durationMs: number
  error?: string
  suite?: string
}

export interface PublishOptions {
  endpoint?: string
  token?: string
  project?: string
  branch?: string
  commit?: string
  tags?: string[]
}

export class TestResultsPublisher {
  private results: TestResult[] = []

  add(result: TestResult) {
    this.results.push(result)
  }

  addMany(results: TestResult[]) {
    this.results.push(...results)
  }

  summary() {
    const passed = this.results.filter(r => r.status === 'passed').length
    const failed = this.results.filter(r => r.status === 'failed').length
    const skipped = this.results.filter(r => r.status === 'skipped').length
    const totalDuration = this.results.reduce((a, r) => a + r.durationMs, 0)
    return {
      total: this.results.length,
      passed,
      failed,
      skipped,
      passRate: this.results.length === 0 ? 0 : (passed / this.results.length) * 100,
      totalDuration
    }
  }

  async publish(options: PublishOptions = {}): Promise<void> {
    const summary = this.summary()
    const payload = {
      project: options.project ?? 'astrovox-ai',
      branch: options.branch ?? 'main',
      commit: options.commit ?? 'unknown',
      results: this.results,
      summary,
      tags: options.tags ?? []
    }
    if (options.endpoint) {
      await fetch(options.endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${options.token ?? ''}` },
        body: JSON.stringify(payload)
      })
    }
  }

  clear() {
    this.results = []
  }
}

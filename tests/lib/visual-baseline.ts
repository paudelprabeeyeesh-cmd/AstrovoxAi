export interface VisualBaselineOptions {
  threshold?: number
  fullPage?: boolean
  name?: string
}

export class VisualRegressionBaseline {
  private baselines = new Map<string, string>()
  private defaults: Required<VisualBaselineOptions> = {
    threshold: 0.01,
    fullPage: false,
    name: 'default'
  }

  register(name: string, snapshot: string) {
    this.baselines.set(name, snapshot)
  }

  compare(name: string, current: string, options: VisualBaselineOptions = {}): boolean {
    const baseline = this.baselines.get(name)
    if (!baseline) {
      this.baselines.set(name, current)
      return true
    }
    const threshold = options.threshold ?? this.defaults.threshold
    const diff = this.computeDiff(baseline, current)
    return diff < threshold
  }

  private computeDiff(a: string, b: string): number {
    if (a === b) return 0
    const maxLen = Math.max(a.length, b.length)
    let diff = 0
    for (let i = 0; i < maxLen; i++) {
      if (a[i] !== b[i]) diff++
    }
    return maxLen === 0 ? 0 : diff / maxLen
  }

  getBaseline(name: string): string | undefined {
    return this.baselines.get(name)
  }

  clear() {
    this.baselines.clear()
  }
}

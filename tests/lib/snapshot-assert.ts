export interface SnapshotAssertOptions {
  tolerance?: number
  ignoreFields?: string[]
  deepEqual?: boolean
}

export class SnapshotAssert {
  private snapshots = new Map<string, unknown>()

  register(name: string, value: unknown) {
    this.snapshots.set(name, value)
  }

  assert<T>(name: string, actual: T, options: SnapshotAssertOptions = {}): void {
    const expected = this.snapshots.get(name)
    if (expected === undefined) {
      throw new Error(`Snapshot "${name}" is not registered. Call register() first.`)
    }
    const tolerance = options.tolerance ?? 0
    const ignoreFields = options.ignoreFields ?? []
    const normalizedActual = this.normalize(actual, ignoreFields)
    const normalizedExpected = this.normalize(expected, ignoreFields)
    if (!options.deepEqual) {
      expect(normalizedActual).toEqual(normalizedExpected)
      return
    }
    if (typeof normalizedActual === 'number' && typeof normalizedExpected === 'number') {
      expect(Math.abs(normalizedActual - normalizedExpected)).toBeLessThanOrEqual(tolerance)
      return
    }
    expect(normalizedActual).toEqual(normalizedExpected)
  }

  assertMatch<T>(name: string, actual: T, matcher: (expected: unknown) => void): void {
    const expected = this.snapshots.get(name)
    if (expected === undefined) {
      throw new Error(`Snapshot "${name}" is not registered.`)
    }
    matcher(expected)
  }

  private normalize(value: unknown, ignoreFields: string[]): unknown {
    if (ignoreFields.length === 0) return value
    if (Array.isArray(value)) return value.map(item => this.normalize(item, ignoreFields))
    if (value && typeof value === 'object') {
      const clone: Record<string, unknown> = {}
      for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
        if (!ignoreFields.includes(k)) clone[k] = this.normalize(v, ignoreFields)
      }
      return clone
    }
    return value
  }
}

export const snapshotAssert = new SnapshotAssert()

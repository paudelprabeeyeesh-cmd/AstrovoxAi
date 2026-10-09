
export interface ChaosScenario {
  inject(): Promise<void>
  recover(): Promise<void>
  verify(): Promise<boolean>
}

export interface ChaosResult {
  success: boolean
  error?: string
  recoveryMs: number
}

export class ChaosRunner {
  private scenarios = new Map<string, ChaosScenario>()

  register(name: string, scenario: ChaosScenario) {
    this.scenarios.set(name, scenario)
  }

  async run(name: string, verifyAfterMs = 100): Promise<ChaosResult> {
    const scenario = this.scenarios.get(name)
    if (!scenario) {
      return { success: false, error: 'Scenario not found', recoveryMs: 0 }
    }
    const start = performance.now()
    try {
      await scenario.inject()
      await new Promise((r) => setTimeout(r, verifyAfterMs))
      await scenario.recover()
      const ok = await scenario.verify()
      return { success: ok, recoveryMs: performance.now() - start }
    } catch (error: any) {
      return { success: false, error: error?.message ?? 'Unknown error', recoveryMs: performance.now() - start }
    }
  }

  async runAll(verifyAfterMs = 100): Promise<ChaosResult[]> {
    const results: ChaosResult[] = []
    for (const name of this.scenarios.keys()) {
      results.push(await this.run(name, verifyAfterMs))
    }
    return results
  }
}

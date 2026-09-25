export interface LoadScenarioOptions {
  name: string
  virtualUsers: number
  durationSeconds: number
  rampUpSeconds?: number
  thinkTimeMs?: number
  maxErrorRate?: number
}

export class LoadTestScenarioBuilder {
  private scenarios: LoadScenarioOptions[] = []

  addScenario(options: LoadScenarioOptions): this {
    this.scenarios.push(options)
    return this
  }

  build(): string[] {
    const scripts: string[] = []
    for (const scenario of this.scenarios) {
      const rampUp = scenario.rampUpSeconds ?? 0
      const thinkTime = scenario.thinkTimeMs ?? 100
      const maxErrorRate = scenario.maxErrorRate ?? 0.01
      scripts.push(`export const config = {
  scenarios: {
    ${scenario.name}: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [{ duration: '${rampUp}s', target: ${scenario.virtualUsers} }],
      gracefulRampDown: '${scenario.durationSeconds}s',
      exec: '${scenario.name.toLowerCase()}_action',
      maxErrorRate: ${maxErrorRate},
      thinkTime: ${thinkTime}
    }
  },
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<${maxErrorRate}']
  }
}`)
    }
    return scripts
  }

  generateK6Script(): string {
    const scripts = this.build()
    return `
import http from 'k6/http'
import { check } from 'k6'

${scripts.join('\n')}

export function ${this.scenarios.map(s => s.name.toLowerCase() + '_action').join(', ')}() {
  const res = http.get('http://localhost:8000/health')
  check(res, { 'status is 200': (r) => r.status === 200 })
}
`
  }
}

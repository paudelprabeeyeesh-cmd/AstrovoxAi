import { describe, it, expect } from 'vitest'
import { LoadTestScenarioBuilder } from '../lib/load-scenario'

describe('load-scenario', () => {
  it('build returns config for single scenario', () => {
    const builder = new LoadTestScenarioBuilder()
    builder.addScenario({ name: 'chat', virtualUsers: 50, durationSeconds: 60 })
    const scripts = builder.build()
    expect(scripts).toHaveLength(1)
    expect(scripts[0]).toContain('chat')
    expect(scripts[0]).toContain('target: 50')
    expect(scripts[0]).toContain('60s')
  })

  it('build returns config for multiple scenarios', () => {
    const builder = new LoadTestScenarioBuilder()
    builder.addScenario({ name: 'chat', virtualUsers: 50, durationSeconds: 60 })
    builder.addScenario({ name: 'search', virtualUsers: 20, durationSeconds: 30 })
    const scripts = builder.build()
    expect(scripts).toHaveLength(2)
  })

  it('build uses default values when omitted', () => {
    const builder = new LoadTestScenarioBuilder()
    builder.addScenario({ name: 'chat', virtualUsers: 10, durationSeconds: 30 })
    const scripts = builder.build()
    expect(scripts[0]).toContain('startVUs: 0')
    expect(scripts[0]).toContain('gracefulRampDown')
  })

  it('generateK6Script returns a valid k6 script', () => {
    const builder = new LoadTestScenarioBuilder()
    builder.addScenario({ name: 'chat', virtualUsers: 50, durationSeconds: 60 })
    const script = builder.generateK6Script()
    expect(script).toContain("import http from 'k6/http'")
    expect(script).toContain('export function')
    expect(script).toContain('http.get')
  })

  it('generateK6Script includes chat action for scenario', () => {
    const builder = new LoadTestScenarioBuilder()
    builder.addScenario({ name: 'ChatTest', virtualUsers: 50, durationSeconds: 60 })
    const script = builder.generateK6Script()
    expect(script).toContain('chattest_action')
  })

  it('builder supports chaining', () => {
    const builder = new LoadTestScenarioBuilder()
    const result = builder.addScenario({ name: 's1', virtualUsers: 10, durationSeconds: 10 })
    expect(result).toBe(builder)
  })
})
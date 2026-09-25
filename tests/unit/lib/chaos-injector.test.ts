import { describe, it, expect, vi } from 'vitest'
import { ChaosFaultInjector } from '../lib/chaos-injector'

describe('chaos-injector', () => {
  it('register stores fault config', () => {
    const injector = new ChaosFaultInjector()
    injector.register('db', { type: 'error', message: 'DB down' })
    expect(injector['faults'].get('db')).toEqual({ type: 'error', message: 'DB down' })
  })

  it('inject throws for error fault', () => {
    const injector = new ChaosFaultInjector()
    injector.register('svc', { type: 'error', message: 'Service error', probability: 1 })
    expect(() => injector.inject('svc')).toThrow('Service error')
  })

  it('inject throws for timeout fault', () => {
    const injector = new ChaosFaultInjector()
    injector.register('timeout', { type: 'timeout', duration: 5000, probability: 1 })
    expect(() => injector.inject('timeout')).toThrow('Request timeout after 5000ms')
  })

  it('inject throws for network fault', () => {
    const injector = new ChaosFaultInjector()
    injector.register('net', { type: 'network', probability: 1 })
    expect(() => injector.inject('net')).toThrow('Network connection lost')
  })

  it('inject throws for payload fault', () => {
    const injector = new ChaosFaultInjector()
    injector.register('payload', { type: 'payload', probability: 1 })
    expect(() => injector.inject('payload')).toThrow('Corrupted payload received')
  })

  it('inject does nothing for unknown key', () => {
    const injector = new ChaosFaultInjector()
    expect(() => injector.inject('missing')).not.toThrow()
  })

  it('inject respects probability', () => {
    const injector = new ChaosFaultInjector()
    injector.register('maybe', { type: 'error', probability: 0 })
    expect(() => injector.inject('maybe')).not.toThrow()
  })

  it('clear removes all faults', () => {
    const injector = new ChaosFaultInjector()
    injector.register('f1', { type: 'error', probability: 1 })
    injector.clear()
    expect(() => injector.inject('f1')).not.toThrow()
  })
})
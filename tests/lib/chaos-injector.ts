export type FaultType = 'latency' | 'error' | 'timeout' | 'payload' | 'network'

export interface FaultOptions {
  type: FaultType
  probability?: number
  duration?: number
  statusCode?: number
  latencyMs?: number
  message?: string
}

export class ChaosFaultInjector {
  private faults: Map<string, FaultOptions> = new Map()

  register(key: string, fault: FaultOptions) {
    this.faults.set(key, fault)
  }

  inject(key: string): void {
    const fault = this.faults.get(key)
    if (!fault) return
    if (Math.random() > (fault.probability ?? 1)) return

    switch (fault.type) {
      case 'latency':
        jest.advanceTimersByTime?.(fault.latencyMs ?? 500) || new Promise(r => setTimeout(r, fault.latencyMs ?? 500))
        break
      case 'error':
        throw new Error(fault.message ?? `Injected ${fault.type} fault`)
      case 'timeout':
        throw new Error(`Request timeout after ${fault.duration ?? 5000}ms`)
      case 'payload':
        throw new Error('Corrupted payload received')
      case 'network':
        throw new Error('Network connection lost')
      default:
        break
    }
  }

  clear() {
    this.faults.clear()
  }
}

export interface ParallelConfig {
  workers: number
  maxConcurrency: number
  timeout: number
  retryAttempts: number
  retryDelay: number
}

export const defaultParallelConfig: ParallelConfig = {
  workers: typeof navigator !== 'undefined' ? navigator.hardwareConcurrency ?? 4 : 4,
  maxConcurrency: 4,
  timeout: 30000,
  retryAttempts: 2,
  retryDelay: 1000
}

export function getParallelConfig(): ParallelConfig {
  return { ...defaultParallelConfig }
}

export function withParallel<T>(
  config: ParallelConfig,
  tasks: Array<() => Promise<T>>
): Promise<T[]> {
  const results: T[] = []
  const executing: Promise<void>[] = []
  for (const task of tasks) {
    const p = task().then(result => { results.push(result) })
    executing.push(p)
    if (executing.length >= config.maxConcurrency) {
      await Promise.race(executing)
    }
  }
  await Promise.all(executing)
  return results
}

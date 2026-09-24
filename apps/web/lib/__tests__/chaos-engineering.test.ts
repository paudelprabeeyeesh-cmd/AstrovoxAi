
import { ChaosRunner } from '@/lib/chaos'

describe('Chaos Engineering Tests', () => {
  it('registers and runs a scenario', async () => {
    const runner = new ChaosRunner()
    const scenario = {
      inject: jest.fn().mockResolvedValue(undefined),
      recover: jest.fn().mockResolvedValue(undefined),
      verify: jest.fn().mockResolvedValue(true),
    }
    runner.register('network-partition', scenario as any)
    const result = await runner.run('network-partition', 0.1)
    expect(result.success).toBe(true)
    expect(scenario.inject).toHaveBeenCalled()
    expect(scenario.recover).toHaveBeenCalled()
    expect(scenario.verify).toHaveBeenCalled()
  })

  it('handles injection failure gracefully', async () => {
    const runner = new ChaosRunner()
    const scenario = {
      inject: jest.fn().mockRejectedValue(new Error('injection failed')),
      recover: jest.fn().mockResolvedValue(undefined),
      verify: jest.fn().mockResolvedValue(false),
    }
    runner.register('fail', scenario as any)
    const result = await runner.run('fail', 0.1)
    expect(result.success).toBe(false)
    expect(result.error).toBeDefined()
  })
})

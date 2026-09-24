
import { runSyntheticCheck, getSyntheticResults } from '@/lib/analytics/synthetic-monitoring'

jest.mock('@/lib/api', () => ({
  api: {
    post: jest.fn(),
    get: jest.fn(),
  },
}))

const mockApi = require('@/lib/api').api

describe('synthetic-monitoring', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('runs synthetic check', async () => {
    mockApi.post.mockResolvedValue({ name: 'health', success: true, latency_ms: 120 })
    const result = await runSyntheticCheck({ name: 'health', url: '/health', expectedStatus: 200 })
    expect(result.name).toBe('health')
    expect(result.success).toBe(true)
  })

  it('fetches synthetic results', async () => {
    mockApi.get.mockResolvedValue([{ name: 'health', success: true }])
    const result = await getSyntheticResults()
    expect(result).toHaveLength(1)
  })

  it('throws on fetch failure', async () => {
    mockApi.post.mockRejectedValue(new Error('network'))
    await expect(runSyntheticCheck({ name: 'health', url: '/health' })).rejects.toThrow('Failed to run synthetic check')
  })
})


import { trackFeatureUse, getFeatureUsage, getFeatureAdoption } from '@/lib/analytics/feature-analytics'

jest.mock('@/lib/api', () => ({
  api: {
    post: jest.fn(),
    get: jest.fn(),
  },
}))

const mockApi = require('@/lib/api').api

describe('feature-analytics', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('tracks feature use without throwing', async () => {
    mockApi.post.mockResolvedValue({})
    await expect(trackFeatureUse('user-1', { feature: 'chat' })).resolves.toBeUndefined()
    expect(mockApi.post).toHaveBeenCalledWith(
      '/analytics/features',
      expect.objectContaining({ user_id: 'user-1', feature: 'chat' }),
    )
  })

  it('fetches feature usage', async () => {
    mockApi.get.mockResolvedValue({ features: [{ feature: 'chat', count: 10 }] })
    const result = await getFeatureUsage()
    expect(result.features).toHaveLength(1)
  })

  it('fetches feature adoption', async () => {
    mockApi.get.mockResolvedValue({ total_users: 100, features: [] })
    const result = await getFeatureAdoption()
    expect(result.total_users).toBe(100)
  })

  it('swallows tracking errors', async () => {
    mockApi.post.mockRejectedValue(new Error('network'))
    await expect(trackFeatureUse('user-1', { feature: 'chat' })).resolves.toBeUndefined()
  })
})

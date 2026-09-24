
import { trackCost, getUserCost } from '@/lib/analytics/cost-tracker'

jest.mock('@/lib/api', () => ({
  api: {
    post: jest.fn(),
    get: jest.fn(),
  },
}))

const mockApi = require('@/lib/api').api

describe('cost-tracker', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('tracks cost without throwing', async () => {
    mockApi.post.mockResolvedValue({})
    await expect(trackCost('user-1', { model: 'gpt-4o', promptTokens: 10, completionTokens: 5, cost: 0.001 })).resolves.toBeUndefined()
    expect(mockApi.post).toHaveBeenCalledWith(
      '/analytics/cost',
      expect.objectContaining({ user_id: 'user-1' }),
    )
  })

  it('fetches user cost', async () => {
    mockApi.get.mockResolvedValue({ total_cost: 1.5, requests: 10 })
    const result = await getUserCost('user-1')
    expect(result).toEqual({ total_cost: 1.5, requests: 10 })
  })

  it('swallows tracking errors', async () => {
    mockApi.post.mockRejectedValue(new Error('network'))
    await expect(trackCost('user-1', { model: 'gpt-4o', promptTokens: 10, completionTokens: 5, cost: 0.001 })).resolves.toBeUndefined()
  })
})

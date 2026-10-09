
import { trackUsage, getUserUsage } from '@/lib/analytics/usage-tracker'

jest.mock('@/lib/api', () => ({
  api: {
    post: jest.fn(),
    get: jest.fn(),
  },
}))

const mockApi = require('@/lib/api').api

describe('usage-tracker', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('tracks usage without throwing', async () => {
    mockApi.post.mockResolvedValue({})
    await expect(trackUsage('user-1', { action: 'login' })).resolves.toBeUndefined()
    expect(mockApi.post).toHaveBeenCalledWith(
      '/analytics/usage',
      expect.objectContaining({ user_id: 'user-1', action: 'login' }),
    )
  })

  it('fetches user usage', async () => {
    mockApi.get.mockResolvedValue({ user_id: 'user-1', usage_count: 5 })
    const result = await getUserUsage('user-1')
    expect(result).toEqual({ user_id: 'user-1', usage_count: 5 })
  })

  it('swallows tracking errors', async () => {
    mockApi.post.mockRejectedValue(new Error('network'))
    await expect(trackUsage('user-1', { action: 'login' })).resolves.toBeUndefined()
  })
})


import { trackTokens, getUserTokens, getTokenTrend } from '@/lib/analytics/token-tracker'

jest.mock('@/lib/api', () => ({
  api: {
    post: jest.fn(),
    get: jest.fn(),
  },
}))

const mockApi = require('@/lib/api').api

describe('token-tracker', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('tracks tokens without throwing', async () => {
    mockApi.post.mockResolvedValue({})
    await expect(trackTokens('user-1', { model: 'gpt-4o', promptTokens: 10, completionTokens: 5 })).resolves.toBeUndefined()
    expect(mockApi.post).toHaveBeenCalledWith(
      '/analytics/tokens',
      expect.objectContaining({ user_id: 'user-1' }),
    )
  })

  it('fetches user tokens', async () => {
    mockApi.get.mockResolvedValue({ total_tokens: 150, requests: 3 })
    const result = await getUserTokens('user-1')
    expect(result).toEqual({ total_tokens: 150, requests: 3 })
  })

  it('fetches token trend', async () => {
    mockApi.get.mockResolvedValue([{ day: '2024-01-01', tokens: 500, requests: 5 }])
    const result = await getTokenTrend()
    expect(result).toHaveLength(1)
  })

  it('swallows tracking errors', async () => {
    mockApi.post.mockRejectedValue(new Error('network'))
    await expect(trackTokens('user-1', { model: 'gpt-4o', promptTokens: 10, completionTokens: 5 })).resolves.toBeUndefined()
  })
})

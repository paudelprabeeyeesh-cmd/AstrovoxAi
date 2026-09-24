
import { getUserAnalytics, getUserActivityTimeline, getUserRetention } from '@/lib/analytics/user-analytics'

jest.mock('@/lib/api', () => ({
  api: {
    get: jest.fn(),
  },
}))

const mockApi = require('@/lib/api').api

describe('user-analytics', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('fetches user analytics', async () => {
    mockApi.get.mockResolvedValue({ user_id: 'user-1', events: [], usage: {} })
    const result = await getUserAnalytics('user-1')
    expect(result.user_id).toBe('user-1')
  })

  it('fetches activity timeline', async () => {
    mockApi.get.mockResolvedValue([])
    const result = await getUserActivityTimeline('user-1')
    expect(Array.isArray(result)).toBe(true)
  })

  it('fetches retention', async () => {
    mockApi.get.mockResolvedValue({ first_seen: '2024-01-01', total_events: 50 })
    const result = await getUserRetention('user-1')
    expect(result.first_seen).toBe('2024-01-01')
  })

  it('throws on fetch failure', async () => {
    mockApi.get.mockRejectedValue(new Error('network'))
    await expect(getUserAnalytics('user-1')).rejects.toThrow('Failed to fetch user analytics')
  })
})

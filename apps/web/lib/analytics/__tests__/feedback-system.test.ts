
import { submitFeedback, getFeedbackSummary, getRecentFeedback } from '@/lib/analytics/feedback-system'

jest.mock('@/lib/api', () => ({
  api: {
    post: jest.fn(),
    get: jest.fn(),
  },
}))

const mockApi = require('@/lib/api').api

describe('feedback-system', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('submits feedback without throwing', async () => {
    mockApi.post.mockResolvedValue({})
    await expect(submitFeedback('user-1', { requestId: 'req-1', rating: 5, comment: 'Great' })).resolves.toBeUndefined()
    expect(mockApi.post).toHaveBeenCalledWith(
      '/analytics/feedback',
      expect.objectContaining({ user_id: 'user-1', rating: 5 }),
    )
  })

  it('fetches feedback summary', async () => {
    mockApi.get.mockResolvedValue({ total_feedback: 10, average_rating: 4.5 })
    const result = await getFeedbackSummary()
    expect(result.total_feedback).toBe(10)
  })

  it('fetches recent feedback', async () => {
    mockApi.get.mockResolvedValue([{ id: 'fb-1', rating: 5 }])
    const result = await getRecentFeedback()
    expect(result).toHaveLength(1)
  })

  it('swallows submission errors', async () => {
    mockApi.post.mockRejectedValue(new Error('network'))
    await expect(submitFeedback('user-1', { requestId: 'req-1', rating: 5 })).resolves.toBeUndefined()
  })
})


import {
  generatePerformanceReport,
  exportPerformanceReportJson,
  exportPerformanceReportCsv,
} from '@/lib/analytics/performance-reports'

jest.mock('@/lib/api', () => ({
  api: {
    get: jest.fn(),
  },
}))

const mockApi = require('@/lib/api').api

describe('performance-reports', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('generates performance report', async () => {
    mockApi.get.mockResolvedValue({
      generated_at: '2024-01-01T00:00:00Z',
      window_days: 7,
      summary: { status: 'healthy' },
    })
    const result = await generatePerformanceReport(undefined, 'user-1', 7)
    expect(result.windowDays).toBe(7)
    expect(result.summary.status).toBe('healthy')
  })

  it('exports report as json', async () => {
    const report = { generatedAt: '2024-01-01T00:00:00Z', windowDays: 7, summary: {} }
    const json = await exportPerformanceReportJson(report)
    expect(JSON.parse(json)).toEqual(report)
  })

  it('exports report as csv', async () => {
    const report = { summary: { status: 'healthy', total_requests: 10 } }
    const csv = await exportPerformanceReportCsv(report)
    expect(csv).toContain('metric,value')
    expect(csv).toContain('status,healthy')
  })

  it('throws on fetch failure', async () => {
    mockApi.get.mockRejectedValue(new Error('network'))
    await expect(generatePerformanceReport()).rejects.toThrow('Failed to generate performance report')
  })
})

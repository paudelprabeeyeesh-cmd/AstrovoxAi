import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ModelPerformanceDashboard from '../../src/components/dashboards/ModelPerformanceDashboard'

describe('ModelPerformanceDashboard', () => {
  const mockModels = [
    { id: '1', name: 'GPT-4', provider: 'OpenAI', status: 'active', latencyP50: 250, latencyP99: 800, throughput: 45.2, errorRate: 0.01, avgTokens: 1500, costPer1K: 0.03 },
    { id: '2', name: 'Claude-3', provider: 'Anthropic', status: 'active', latencyP50: 300, latencyP99: 900, throughput: 40.5, errorRate: 0.005, avgTokens: 1800, costPer1K: 0.025 }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders model list', () => {
    render(<ModelPerformanceDashboard models={mockModels} />)
    expect(screen.getByText('GPT-4')).toBeDefined()
    expect(screen.getByText('Claude-3')).toBeDefined()
  })

  it('shows performance metrics', () => {
    render(<ModelPerformanceDashboard models={mockModels} />)
    expect(screen.getByText('250ms')).toBeDefined()
    expect(screen.getByText('800ms')).toBeDefined()
  })

  it('switches between models', () => {
    render(<ModelPerformanceDashboard models={mockModels} />)
    const select = screen.getByRole('combobox')
    fireEvent.change(select, { target: { value: '2' } })
    expect(screen.getByText('Claude-3')).toBeDefined()
  })

  it('shows active status badge', () => {
    render(<ModelPerformanceDashboard models={mockModels} />)
    expect(screen.getByText('Active')).toBeDefined()
  })
})

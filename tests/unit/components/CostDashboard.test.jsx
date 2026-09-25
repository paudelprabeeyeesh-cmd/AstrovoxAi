import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import CostDashboard from '../../src/components/dashboards/CostDashboard'

describe('CostDashboard', () => {
  const mockCosts = [
    { model: 'gpt-4', cost: 12.50, tokens: 50000, date: '2025-01-15' },
    { model: 'gpt-4', cost: 8.30, tokens: 30000, date: '2025-01-16' },
    { model: 'claude-3', cost: 5.20, tokens: 20000, date: '2025-01-15' }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders cost dashboard', () => {
    render(<CostDashboard costs={mockCosts} />)
    expect(screen.getByText('Cost Dashboard')).toBeDefined()
  })

  it('calculates total cost', () => {
    render(<CostDashboard costs={mockCosts} />)
    expect(screen.getByText('$26.00')).toBeDefined()
  })

  it('filters by model', () => {
    render(<CostDashboard costs={mockCosts} />)
    const select = screen.getByRole('combobox')
    fireEvent.change(select, { target: { value: 'claude-3' } })
    expect(screen.getByText('$5.20')).toBeDefined()
  })

  it('shows daily chart', () => {
    render(<CostDashboard costs={mockCosts} />)
    expect(screen.getByText('Daily Cost')).toBeDefined()
  })
})

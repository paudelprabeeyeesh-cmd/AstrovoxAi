import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import AnalyticsDashboard from '../src/components/dashboards/AnalyticsDashboard'

describe('AnalyticsDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders analytics header', () => {
    render(<AnalyticsDashboard data={{}} timeRange="7d" />)
    expect(screen.getByText('Analytics Dashboard')).toBeDefined()
  })

  it('shows metric cards', () => {
    render(<AnalyticsDashboard data={{}} timeRange="7d" />)
    expect(screen.getByText('Total Messages')).toBeDefined()
    expect(screen.getByText('Active Users')).toBeDefined()
  })

  it('changes time range', () => {
    render(<AnalyticsDashboard data={{}} timeRange="7d" />)
    const select = screen.getByRole('combobox')
    fireEvent.change(select, { target: { value: '30d' } })
    expect(screen.getByText('Last 30 days')).toBeDefined()
  })
})
